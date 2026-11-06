import math
import numpy as np
from datetime import timedelta
from sqlalchemy import select
from fastapi import HTTPException
from .models import DemandHistory, DemandForecast, ForecastEvaluation

def metrics(actual, predicted):
    a, p = np.asarray(actual), np.asarray(predicted)
    err = np.abs(a-p)
    nz = a != 0
    return {'MAE': float(err.mean()), 'RMSE': float(np.sqrt(np.mean((a-p)**2))),
            'MAPE': float(np.mean(err[nz]/a[nz])*100) if nz.any() else None,
            'WAPE': float(err.sum()/a.sum()*100) if a.sum() else None}

def predict(values, horizon, model):
    y = np.asarray(values, dtype=float)
    if model == 'Moving average':
        return np.full(horizon, y[-28:].mean())
    if model == 'Exponential smoothing':
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        return np.maximum(0, ExponentialSmoothing(y, trend='add', seasonal='add', seasonal_periods=7, initialization_method='estimated').fit().forecast(horizon))
    if model == 'ARIMA':
        from statsmodels.tsa.arima.model import ARIMA
        return np.maximum(0, ARIMA(y, order=(2, 0, 1)).fit().forecast(horizon))
    if model in ['Random forest', 'XGBoost']:
        from sklearn.ensemble import RandomForestRegressor
        if model == 'XGBoost':
            from xgboost import XGBRegressor
            estimator = XGBRegressor(n_estimators=60, max_depth=3, random_state=42, n_jobs=1)
        else:
            estimator = RandomForestRegressor(n_estimators=60, max_depth=6, random_state=42, n_jobs=1)
        lag = 14
        x = [y[i-lag:i].tolist()+[i%7] for i in range(lag, len(y))]
        estimator.fit(x, y[lag:])
        history = y.tolist()
        forecast = []
        for _ in range(horizon):
            value = max(0, float(estimator.predict([history[-lag:]+[len(history)%7]])[0]))
            forecast.append(value); history.append(value)
        return np.asarray(forecast)
    raise ValueError('Unknown forecast model')

def run_forecast(db, product_id, horizon=30, advanced=False):
    rows = db.scalars(select(DemandHistory).where(DemandHistory.product_id == product_id).order_by(DemandHistory.day)).all()
    if len(rows) < 90:
        raise HTTPException(422, 'At least 90 daily demand observations are required')
    if any((b.day-a.day).days != 1 for a, b in zip(rows, rows[1:])):
        raise HTTPException(422, 'Demand history must contain consecutive daily observations')
    y = np.array([r.quantity for r in rows], dtype=float)
    train_end, validation_end = int(len(y)*.6), int(len(y)*.8)
    names = ['Moving average', 'Exponential smoothing', 'Random forest'] + (['ARIMA', 'XGBoost'] if advanced else [])
    comparison, errors = [], []
    for name in names:
        try:
            val = predict(y[:train_end], validation_end-train_end, name)
            comparison.append({'model': name, **metrics(y[train_end:validation_end], val)})
        except Exception as exc:
            errors.append(f'{name}: {type(exc).__name__}')
    if not comparison:
        raise HTTPException(500, 'All forecast models failed')
    selected = min(comparison, key=lambda m: m['MAE'])['model']
    test_prediction = predict(y[:validation_end], len(y)-validation_end, selected)
    test_metrics = metrics(y[validation_end:], test_prediction)
    residual_sigma = float(np.std(y[train_end:validation_end]-predict(y[:train_end], validation_end-train_end, selected)))
    future = predict(y, horizon, selected)
    result = {'product_id': product_id, 'model': selected, 'horizon': horizon, 'comparison': comparison, 'test_metrics': test_metrics,
              'split': {'train': train_end, 'validation': validation_end-train_end, 'test': len(y)-validation_end},
              'history': [{'date': r.day.isoformat(), 'actual': r.quantity} for r in rows[-90:]],
              'forecast': [{'date': (rows[-1].day+timedelta(days=i+1)).isoformat(), 'predicted': round(float(v), 2), 'lower': round(max(0, float(v)-1.96*residual_sigma), 2), 'upper': round(float(v)+1.96*residual_sigma, 2)} for i, v in enumerate(future)],
              'limitations': ['Synthetic history', 'Intervals are approximate residual bands, not calibrated prediction intervals', 'Model selected on validation MAE; test used only for reporting'], 'warnings': errors}
    db.add(DemandForecast(product_id=product_id, result=result))
    db.add(ForecastEvaluation(product_id=product_id, result={'model': selected, **test_metrics}))
    db.flush()
    return result
