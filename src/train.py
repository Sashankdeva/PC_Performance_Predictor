"""Train and compare regression models that predict Performance_Score.

Learning type: supervised learning (regression). Every training example is a PC
whose Performance_Score is known, and the models learn the mapping from the 8
attributes to that score.

Each model is wrapped in a pipeline (one-hot OS + scaled numbers) so encoding
and scaling are fitted on the training split only. Hyperparameters are tuned
with 5-fold cross-validation, the best model is chosen by CV RMSE, evaluated on
the held-out test set, and saved to models/.
"""
import json
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (AdaBoostRegressor, BaggingRegressor, GradientBoostingRegressor,
                              RandomForestRegressor)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "pc_performance_cleaned.csv"
MODEL_PATH = ROOT / "models" / "performance_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
FIG_DIR = ROOT / "reports" / "figures"

NUMERIC_FEATURES = ["RAM_GB", "CPU_Cores", "GPU_Level", "Storage_GB",
                    "Clock_GHz", "Age_Years", "Temperature_C"]
CATEGORICAL_FEATURES = ["OS"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "Performance_Score"
SEED = 42

CANDIDATES = {
    "Linear Regression": (LinearRegression(), {}),
    "Ridge Regression": (Ridge(), {"model__alpha": [0.1, 1, 10]}),
    "KNN": (KNeighborsRegressor(),
            {"model__n_neighbors": [3, 5, 7, 11], "model__weights": ["uniform", "distance"],
             "model__metric": ["euclidean", "manhattan"]}),
    "SVR": (SVR(), {"model__kernel": ["linear", "rbf"], "model__C": [100, 500, 1000],
                    "model__epsilon": [1, 10]}),
    "Decision Tree": (DecisionTreeRegressor(random_state=SEED),
                      {"model__max_depth": [4, 6, 8, None], "model__min_samples_leaf": [1, 5]}),
    "Random Forest": (RandomForestRegressor(random_state=SEED),
                      {"model__n_estimators": [300], "model__max_depth": [None, 10],
                       "model__min_samples_leaf": [1, 3]}),
    "Gradient Boosting": (GradientBoostingRegressor(random_state=SEED),
                          {"model__n_estimators": [200, 400], "model__learning_rate": [0.05, 0.1],
                           "model__max_depth": [2, 3]}),
    "Bagging": (BaggingRegressor(DecisionTreeRegressor(), n_estimators=200, random_state=SEED),
                {"model__max_samples": [0.7, 1.0]}),
    "AdaBoost": (AdaBoostRegressor(DecisionTreeRegressor(max_depth=4), random_state=SEED),
                 {"model__n_estimators": [100, 300], "model__learning_rate": [0.05, 0.1, 0.5]}),
}

# Model family and the syllabus unit that covers it
MODEL_INFO = {
    "Linear Regression": ("Linear model", "Unit III"),
    "Ridge Regression": ("Linear model + L2 regularization", "Unit III / V"),
    "KNN": ("Instance-based learning", "Unit II"),
    "SVR": ("Support Vector Machine", "Unit III"),
    "Decision Tree": ("Tree", "Unit V (base learner)"),
    "Random Forest": ("Ensemble: bagging", "Unit V"),
    "Gradient Boosting": ("Ensemble: boosting", "Unit V"),
    "Bagging": ("Ensemble: bagging", "Unit V"),
    "AdaBoost": ("Ensemble: boosting", "Unit V"),
}
RIDGE_ALPHAS = [0.01, 0.1, 1, 10, 100, 1000, 10000]
# Simplest first: used by the one-standard-error rule when models are statistically tied
SIMPLICITY_ORDER = ["Linear Regression", "Ridge Regression", "KNN", "Decision Tree", "SVR",
                    "Random Forest", "Bagging", "Gradient Boosting", "AdaBoost"]


def build_pipeline(model) -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    return Pipeline([("preprocess", preprocess), ("model", model)])


def regression_metrics(y_true, y_pred) -> dict:
    mse = mean_squared_error(y_true, y_pred)
    return {"MAE": mean_absolute_error(y_true, y_pred), "MSE": mse,
            "RMSE": float(np.sqrt(mse)), "R2": r2_score(y_true, y_pred)}


def main():
    df = pd.read_csv(CLEAN_PATH)
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED)
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    results = []
    fitted = {}
    for name, (model, grid) in CANDIDATES.items():
        search = GridSearchCV(build_pipeline(model), grid, cv=cv,
                              scoring="neg_root_mean_squared_error", n_jobs=-1)
        search.fit(X_train, y_train)
        test_scores = regression_metrics(y_test, search.predict(X_test))
        family, unit = MODEL_INFO[name]
        results.append({"Model": name, "Family": family, "Unit": unit,
                        "CV_RMSE": -search.best_score_,
                        "CV_RMSE_Std": search.cv_results_["std_test_score"][search.best_index_],
                        # Train vs test R2 shows bias (both low) and variance (big gap)
                        "Train_R2": r2_score(y_train, search.predict(X_train)),
                        **{f"Test_{k}": v for k, v in test_scores.items()},
                        "Best_Params": search.best_params_})
        fitted[name] = search.best_estimator_

    table = pd.DataFrame(results).sort_values("CV_RMSE").reset_index(drop=True)
    print(table.drop(columns=["Best_Params", "Family", "Unit"]).round(3).to_string(index=False))

    # Model selection uses CV scores only, so the test set stays unbiased.
    # One-standard-error rule: among models whose CV RMSE is within one standard
    # error of the best, pick the simplest (Occam's razor).
    top = table.loc[0]
    threshold = top["CV_RMSE"] + top["CV_RMSE_Std"] / np.sqrt(cv.get_n_splits())
    tied = table[table["CV_RMSE"] <= threshold]["Model"].tolist()
    best_name = min(tied, key=SIMPLICITY_ORDER.index)
    print(f"\nLowest CV RMSE: {top['Model']} ({top['CV_RMSE']:.2f}); within one standard error "
          f"(<= {threshold:.2f}): {', '.join(tied)}")
    best_model = fitted[best_name]
    best_row = table.set_index("Model").loc[best_name]
    print(f"\nBest model: {best_name}  (test R2 = {best_row['Test_R2']:.3f}, "
          f"RMSE = {best_row['Test_RMSE']:.2f})")

    # Refit the chosen configuration on all clean data for the app
    final_model = build_pipeline(best_model.named_steps["model"]).fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    importance = permutation_importance(best_model, X_test, y_test, n_repeats=20,
                                        random_state=SEED, scoring="r2")
    importance = pd.Series(importance.importances_mean, index=FEATURES).sort_values()

    # Regularization: how the L2 penalty strength changes Ridge's CV error
    ridge_sweep = {str(a): float(-cross_val_score(build_pipeline(Ridge(alpha=a)), X_train, y_train,
                                                  cv=cv, scoring="neg_root_mean_squared_error").mean())
                   for a in RIDGE_ALPHAS}

    metrics = {
        "best_model": best_name,
        "learning_type": "Supervised learning (regression)",
        "selection_rule": f"One-standard-error rule: simplest model within {threshold:.2f} CV RMSE "
                          f"(best {top['Model']} {top['CV_RMSE']:.2f})",
        "tied_models": tied,
        "test_metrics": {k.replace("Test_", ""): float(best_row[k])
                         for k in ["Test_MAE", "Test_MSE", "Test_RMSE", "Test_R2"]},
        "comparison": table.drop(columns="Best_Params").round(4).to_dict(orient="records"),
        "feature_importance": importance.round(4).to_dict(),
        "ridge_alpha_cv_rmse": ridge_sweep,
        "best_params": {r["Model"]: r["Best_Params"] for r in results},
        "train_rows": len(X_train), "test_rows": len(X_test),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=str))

    save_figures(table, best_name, y_test, best_model.predict(X_test), importance)
    print(f"Saved model to {MODEL_PATH}")


def save_figures(table, best_name, y_test, y_pred, importance):
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ordered = table.sort_values("Test_R2")
    ax.barh(ordered["Model"], ordered["Test_R2"], color="#4C72B0")
    ax.set_xlabel("Test R²")
    ax.set_title("Model comparison")
    ax.set_xlim(0, 1)
    for i, v in enumerate(ordered["Test_R2"]):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "model_comparison.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(y_test, y_pred, alpha=0.7, color="#4C72B0")
    lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    ax.plot(lims, lims, "--", color="gray")
    ax.set_xlabel("Actual Performance_Score")
    ax.set_ylabel("Predicted Performance_Score")
    ax.set_title(f"{best_name}: actual vs predicted")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "actual_vs_predicted.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(importance.index, importance.values, color="#4C72B0")
    ax.set_xlabel("Drop in R² when feature is shuffled")
    ax.set_title("Feature importance (permutation)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "feature_importance.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
