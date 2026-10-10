# Syllabus mapping — Machine Learning (241AI005)

**Learning type used: Supervised learning — Regression.**
Every training example is a PC with a known `Performance_Score` (the label), and the
models learn to map the 8 attributes to that score. No unsupervised learning (clustering)
is used, because the task has a labelled numeric target.

| Unit | Syllabus topic | Where it is used in this project |
|---|---|---|
| I | Types of ML systems | Supervised (labelled target), batch learning, model-based (learns weights, not lookups) |
| I | Main challenges of ML | Poor-quality data (missing, duplicate, impossible values), small dataset (503 rows), overfitting vs underfitting |
| I | Statistical learning: supervised learning, the learning problem | Learn f(attributes) → Performance_Score from 402 labelled training PCs |
| I | Practice: preprocessing and analysing a dataset | `src/preprocess.py`: 7 cleaning steps, 520 → 503 rows; correlation and class-distribution analysis |
| II | Instance-based learning: kNN, distance-weighted kNN, distance metrics | `KNN` model: k ∈ {3,5,7,11}, uniform vs distance weights, Euclidean vs Manhattan (best: k=7, distance-weighted, Euclidean) |
| II | Bayesian learning: MLE | Ordinary least squares in Linear Regression is the maximum-likelihood estimate under Gaussian noise |
| III | Linear Regression | **Final model** (test R² = 0.929, RMSE = 44.1) |
| III | Support Vector Machines: soft margin, non-linear boundary, kernel functions, RBF | `SVR` model: linear vs RBF (non-linear) kernel, C and ε tuned; the linear kernel wins, confirming the data is linear |
| IV | Hypothesis evaluation: scores, sampling, cross-validation | 80/20 train/test split, 5-fold cross-validation with GridSearchCV, MAE / MSE / RMSE / R² |
| IV | Practice: bias, variance, remove duplicates, cross-validation | Train vs test R² per model (bias/variance), duplicate removal in preprocessing, 5-fold CV |
| IV | Practice: one-hot encoding, categorical encoding | OS standardized (11 spellings plus blanks → 2 categories) and one-hot encoded inside the pipeline |
| V | Ensemble learning: bagging, boosting, AdaBoost, Random Forest | `Bagging`, `Random Forest` (bagging), `Gradient Boosting`, `AdaBoost` (boosting) all trained and compared |
| V | Training vs testing, generalization, overfitting | KNN: train R² 1.00 vs test 0.80 (overfits); Linear: 0.92 vs 0.93 (generalizes) |
| V | Regularization and validation | Ridge (L2) α sweep from 0.01 to 10,000: large α underfits (CV RMSE 48 → 160) |
| V | Theory of generalization (Occam's razor) | One-standard-error rule: SVR, Linear and Ridge are statistically tied, so the simplest (Linear Regression) is chosen |

## Not used (and why)
- **Clustering (Unit IV: k-means, hierarchical, DBSCAN)** — unsupervised; our data has a labelled target.
- **Logistic Regression, Naive Bayes, classification metrics (accuracy, precision, recall, F1, ROC)** —
  the project predicts the numeric score (regression), not a class.
- **Concept learning (Find-S, Candidate Elimination)** — designed for boolean concepts, not numeric prediction.

## Model results (5-fold CV on 402 training rows, test on 101 rows)
| Model | Family (unit) | CV RMSE | Train R² | Test R² |
|---|---|---|---|---|
| SVR (linear kernel) | SVM (III) | 47.32 ± 6.73 | 0.919 | 0.929 |
| **Linear Regression** | Linear model (III) | 47.88 ± 6.32 | 0.920 | **0.929** |
| Ridge Regression | Linear + L2 (III / V) | 47.88 ± 6.32 | 0.920 | 0.929 |
| Gradient Boosting | Boosting (V) | 55.67 ± 4.52 | 0.958 | 0.871 |
| Bagging | Bagging (V) | 69.12 ± 4.65 | 0.974 | 0.822 |
| Random Forest | Bagging (V) | 69.22 ± 4.70 | 0.975 | 0.819 |
| AdaBoost | Boosting (V) | 76.08 ± 5.52 | 0.904 | 0.763 |
| KNN | Instance-based (II) | 82.71 ± 7.39 | 1.000 | 0.798 |
| Decision Tree | Tree (V base learner) | 98.43 ± 3.07 | 0.873 | 0.672 |
