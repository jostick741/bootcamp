from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    from .project_config import get_forecast_horizons
    from .load_data import refresh_sql_result_table
except ImportError:
    from project_config import get_forecast_horizons
    from load_data import refresh_sql_result_table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
INPUT_PATH = PROCESSED_DIR / "etapa1_temporal.csv"
PREDICTIONS_PATH = PROCESSED_DIR / "etapa1_temporal_predicciones.csv"
FORECAST_OUTPUT_PATH = PROCESSED_DIR / "forecast_ev.csv"
METRICS_PATH = MODELS_DIR / "etapa1_baseline_metrics.json"
FEATURE_IMPORTANCE_PATH = MODELS_DIR / "etapa1_baseline_feature_summary.csv"
COMPARISON_PATH = MODELS_DIR / "etapa1_model_comparison.json"
PREDICTIONS_TABLE = "etapa1_temporal_predicciones"
FORECAST_TABLE = "forecast_ev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrena el baseline temporal de adopcion EV.")
    parser.add_argument(
        "--forecast-horizons",
        type=int,
        nargs="+",
        default=None,
        help="Horizontes futuros en anios para proyectar ETAPA 1.",
    )
    return parser.parse_args()



def load_temporal_dataset() -> pd.DataFrame:
    dataframe = pd.read_csv(INPUT_PATH)
    dataframe["anio"] = pd.to_numeric(dataframe["anio"], errors="coerce")
    dataframe["cantidad_ev"] = pd.to_numeric(dataframe["cantidad_ev"], errors="coerce")
    dataframe = dataframe.dropna(subset=["anio", "departamento", "tipo_vehiculo", "cantidad_ev"])
    dataframe = dataframe.sort_values(["anio", "departamento", "tipo_vehiculo"]).reset_index(drop=True)
    return dataframe



def build_model(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )

    regressor = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=1,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ]
    )



def split_temporal(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_years = sorted(dataframe["anio"].dropna().unique())
    if len(unique_years) < 2:
        raise ValueError("Se requieren al menos dos años para una validación temporal.")

    cutoff_year = unique_years[-2] if len(unique_years) > 2 else unique_years[0]
    train_df = dataframe[dataframe["anio"] <= cutoff_year].copy()
    test_df = dataframe[dataframe["anio"] > cutoff_year].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("La partición temporal resultó vacía. Revisa la cobertura temporal del dataset.")

    return train_df, test_df



def summarize_feature_importance(model: Pipeline) -> pd.DataFrame:
    preprocessor = model.named_steps["preprocessor"]
    regressor = model.named_steps["regressor"]
    feature_names = preprocessor.get_feature_names_out()
    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": regressor.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    return importance_df


def prepare_future_feature_frame(dataframe: pd.DataFrame, forecast_horizons: list[int]) -> tuple[pd.DataFrame, int]:
    base_year = int(dataframe["anio"].max())
    latest_feature_df = (
        dataframe.sort_values(["departamento", "tipo_vehiculo", "anio"])
        .groupby(["departamento", "tipo_vehiculo"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    future_frames: list[pd.DataFrame] = []
    for horizon in forecast_horizons:
        horizon_df = latest_feature_df.copy()
        horizon_df["anio_base"] = base_year
        horizon_df["horizonte_anios"] = int(horizon)
        horizon_df["anio"] = base_year + int(horizon)
        future_frames.append(horizon_df)

    future_df = pd.concat(future_frames, ignore_index=True)
    return future_df, base_year


def build_group_trend_lookup(dataframe: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    grouped_df = (
        dataframe.groupby(["departamento", "tipo_vehiculo", "anio"], dropna=False)["cantidad_ev"]
        .sum()
        .reset_index()
        .sort_values(["departamento", "tipo_vehiculo", "anio"])
    )

    trend_lookup: dict[tuple[str, str], dict[str, float]] = {}
    for (departamento, tipo_vehiculo), group_df in grouped_df.groupby(
        ["departamento", "tipo_vehiculo"],
        dropna=False,
    ):
        years = pd.to_numeric(group_df["anio"], errors="coerce").to_numpy(dtype=float)
        values = pd.to_numeric(group_df["cantidad_ev"], errors="coerce").fillna(0).to_numpy(dtype=float)
        valid_mask = ~np.isnan(years)
        years = years[valid_mask]
        values = values[valid_mask]

        if len(years) >= 2 and len(np.unique(years)) >= 2:
            slope, intercept = np.polyfit(years, values, 1)
        elif len(values) >= 1:
            slope = 0.0
            intercept = float(values[-1])
        else:
            slope = 0.0
            intercept = 0.0

        trend_lookup[(departamento, tipo_vehiculo)] = {
            "slope": float(slope),
            "intercept": float(intercept),
        }
    return trend_lookup


def predict_group_trend(history_df: pd.DataFrame, target_df: pd.DataFrame) -> np.ndarray:
    trend_lookup = build_group_trend_lookup(history_df)
    predictions: list[float] = []

    for row in target_df[["departamento", "tipo_vehiculo", "anio"]].itertuples(index=False):
        trend = trend_lookup.get((row.departamento, row.tipo_vehiculo))
        if trend is None:
            predictions.append(0.0)
            continue

        prediction = trend["intercept"] + trend["slope"] * float(row.anio)
        predictions.append(max(prediction, 0.0))

    return np.asarray(predictions, dtype=float)


def evaluate_model(
    model_name: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> tuple[Pipeline, np.ndarray, dict[str, float]]:
    numeric_features = [column for column in feature_columns if column in {"anio", "kwh_promedio", "potencia_carga", "consumo_wh_km"}]
    categorical_features = [column for column in feature_columns if column in {"departamento", "tipo_vehiculo"}]

    model = build_model(numeric_features=numeric_features, categorical_features=categorical_features)
    model.fit(train_df[feature_columns], train_df[target_column])
    predictions = model.predict(test_df[feature_columns])

    metrics = {
        "mae": float(mean_absolute_error(test_df[target_column], predictions)),
        "rmse": float(np.sqrt(mean_squared_error(test_df[target_column], predictions))),
        "r2": float(r2_score(test_df[target_column], predictions)),
    }
    print(f"{model_name}: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}")
    return model, predictions, metrics


def evaluate_group_trend_model(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_column: str,
) -> tuple[np.ndarray, dict[str, float]]:
    predictions = predict_group_trend(train_df, test_df)
    metrics = {
        "mae": float(mean_absolute_error(test_df[target_column], predictions)),
        "rmse": float(np.sqrt(mean_squared_error(test_df[target_column], predictions))),
        "r2": float(r2_score(test_df[target_column], predictions)),
    }
    print(
        "proyeccion_tendencial_grupo: "
        f"MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}"
    )
    return predictions, metrics



def run_baseline(forecast_horizons: list[int] | None = None) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dataframe = load_temporal_dataset()
    train_df, test_df = split_temporal(dataframe)
    forecast_horizons = get_forecast_horizons(forecast_horizons)

    temporal_feature_columns = [
        "anio",
        "departamento",
        "tipo_vehiculo",
    ]
    hybrid_feature_columns = [
        "anio",
        "departamento",
        "tipo_vehiculo",
        "kwh_promedio",
        "potencia_carga",
        "consumo_wh_km",
    ]
    target_column = "cantidad_ev"

    temporal_model, temporal_predictions, temporal_metrics = evaluate_model(
        model_name="modelo_temporal_puro",
        train_df=train_df,
        test_df=test_df,
        feature_columns=temporal_feature_columns,
        target_column=target_column,
    )
    hybrid_model, hybrid_predictions, hybrid_metrics = evaluate_model(
        model_name="modelo_hibrido_energetico",
        train_df=train_df,
        test_df=test_df,
        feature_columns=hybrid_feature_columns,
        target_column=target_column,
    )
    trend_predictions, trend_metrics = evaluate_group_trend_model(
        train_df=train_df,
        test_df=test_df,
        target_column=target_column,
    )

    if temporal_metrics["rmse"] <= hybrid_metrics["rmse"]:
        selected_model_name = "modelo_temporal_puro"
        selected_model = temporal_model
        selected_predictions = temporal_predictions
        selected_metrics = temporal_metrics
        selected_features = temporal_feature_columns
    else:
        selected_model_name = "modelo_hibrido_energetico"
        selected_model = hybrid_model
        selected_predictions = hybrid_predictions
        selected_metrics = hybrid_metrics
        selected_features = hybrid_feature_columns

    if trend_metrics["rmse"] < selected_metrics["rmse"]:
        selected_model_name = "proyeccion_tendencial_grupo"
        selected_model = None
        selected_predictions = trend_predictions
        selected_metrics = trend_metrics
        selected_features = ["anio", "departamento", "tipo_vehiculo"]

    prediction_df = test_df.copy()
    prediction_df["tipo_prediccion"] = "backtest"
    prediction_df["anio_base"] = pd.NA
    prediction_df["horizonte_anios"] = pd.NA
    prediction_df["cantidad_ev_pred_modelo_a"] = temporal_predictions
    prediction_df["cantidad_ev_pred_modelo_b"] = hybrid_predictions
    prediction_df["cantidad_ev_pred_tendencia"] = trend_predictions
    prediction_df["cantidad_ev_pred"] = selected_predictions
    prediction_df["modelo_seleccionado"] = selected_model_name
    prediction_df["error_absoluto"] = (prediction_df[target_column] - prediction_df["cantidad_ev_pred"]).abs()
    prediction_df.to_csv(PREDICTIONS_PATH, index=False)
    refresh_sql_result_table(prediction_df, PREDICTIONS_TABLE)

    future_feature_df, base_year = prepare_future_feature_frame(dataframe, forecast_horizons)
    future_prediction_df = future_feature_df.copy()
    future_prediction_df["tipo_prediccion"] = "forecast_futuro"
    future_prediction_df["cantidad_ev"] = np.nan
    future_prediction_df["cantidad_ev_pred_modelo_a"] = temporal_model.predict(
        future_feature_df[temporal_feature_columns]
    )
    future_prediction_df["cantidad_ev_pred_modelo_b"] = hybrid_model.predict(
        future_feature_df[hybrid_feature_columns]
    )
    future_prediction_df["cantidad_ev_pred_tendencia"] = predict_group_trend(dataframe, future_feature_df)
    future_prediction_df["cantidad_ev_pred"] = (
        future_prediction_df["cantidad_ev_pred_tendencia"].clip(lower=0).round().astype(float)
    )
    future_prediction_df["cantidad_ev_pred_modelo_a"] = future_prediction_df[
        "cantidad_ev_pred_modelo_a"
    ].clip(lower=0)
    future_prediction_df["cantidad_ev_pred_modelo_b"] = future_prediction_df[
        "cantidad_ev_pred_modelo_b"
    ].clip(lower=0)
    future_prediction_df["cantidad_ev_pred_tendencia"] = future_prediction_df[
        "cantidad_ev_pred_tendencia"
    ].clip(lower=0)
    future_prediction_df["modelo_seleccionado"] = "proyeccion_tendencial_grupo"
    future_prediction_df["error_absoluto"] = pd.NA
    future_prediction_df.to_csv(FORECAST_OUTPUT_PATH, index=False)
    refresh_sql_result_table(future_prediction_df, FORECAST_TABLE)

    metrics = {
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "cutoff_year": int(train_df["anio"].max()),
        "base_year": base_year,
        "test_years": sorted(int(year) for year in test_df["anio"].unique()),
        "forecast_horizons_anios": forecast_horizons,
        "forecast_years": sorted(int(year) for year in future_prediction_df["anio"].unique()),
        "selected_model": selected_model_name,
        "future_forecast_method": "proyeccion_tendencial_grupo",
        "selected_features": selected_features,
        "mae": selected_metrics["mae"],
        "rmse": selected_metrics["rmse"],
        "r2": selected_metrics["r2"],
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    COMPARISON_PATH.write_text(
        json.dumps(
            {
                "modelo_temporal_puro": temporal_metrics,
                "modelo_hibrido_energetico": hybrid_metrics,
                "proyeccion_tendencial_grupo": trend_metrics,
                "selected_model": selected_model_name,
                "future_forecast_method": "proyeccion_tendencial_grupo",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    feature_importance_df = summarize_feature_importance(selected_model)
    feature_importance_df.to_csv(FEATURE_IMPORTANCE_PATH, index=False)

    print(f"Baseline temporal entrenado correctamente. Modelo seleccionado: {selected_model_name}")
    print(f"Predicciones guardadas en: {PREDICTIONS_PATH}")
    print(f"Forecast futuro guardado en: {FORECAST_OUTPUT_PATH}")
    print(f"Metricas guardadas en: {METRICS_PATH}")


def main() -> None:
    args = parse_args()
    run_baseline(forecast_horizons=args.forecast_horizons)


if __name__ == "__main__":
    main()
