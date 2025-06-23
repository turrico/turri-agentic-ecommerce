from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.recommendation_system.update_analytics import (
    update_customer_profiles_based_on_analytics,
)
from src.turri_data_hub.recommendation_system.update_woocommerce import (
    update_customer_profiles_based_on_orders,
)
from src.turri_data_hub.update.fetch_all_woocommerce import fetch_all_wocommerce_data
from src.turri_data_hub.update.fetch_google_anylytics_data import (
    fetch_google_analytics_data,
)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/fetch-woocommerce-data")
async def fetch_woocommerce_data(request: Request):
    try:
        await fetch_all_wocommerce_data()
        return {
            "status": "success",
            "message": "All WooCommerce data fetched and saved.",
        }
    except Exception as e:
        logger.exception("Failed to fetch all WooCommerce data")
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@admin_router.post("/fetch-bigquery-data")
async def fetch_bigquery_data(request: Request):
    try:
        db: TurriDB = request.app.state.db
        await fetch_google_analytics_data(db)
        return {
            "status": "success",
            "message": "Google Analytics data fetched and saved.",
        }
    except Exception as e:
        logger.exception("Failed to fetch Google Analytics data")
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@admin_router.post("/update-customer-profiles-woocommerce")
async def update_customer_profiles_no_body(request: Request, from_date: str):
    """
    Updates customer profiles based on WooCommerce orders since a given date.
    Expects a query parameter: from_date=YYYY-MM-DD
    """
    try:
        if not from_date:
            raise HTTPException(
                status_code=400, detail="from_date is required (YYYY-MM-DD)"
            )
        from_date_dt = datetime.fromisoformat(from_date)
        db: TurriDB = request.app.state.db
        success, failures = await update_customer_profiles_based_on_orders(
            db, from_date_dt
        )
        return {
            "status": "success",
            "message": f"Customer profiles updated. Success: {success}, Failures: {failures}",
            "success": success,
            "failures": failures,
        }
    except Exception as e:
        logger.exception("Failed to update customer profiles")
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@admin_router.post("/update-customer-profiles-analytics")
async def update_customer_profiles_analytics(request: Request, from_date: str):
    """
    Updates customer profiles based on Google Analytics data since a given date.
    Expects a query parameter: from_date=YYYY-MM-DD
    """
    try:
        if not from_date:
            raise HTTPException(
                status_code=400, detail="from_date is required (YYYY-MM-DD)"
            )
        from_date_dt = datetime.fromisoformat(from_date)
        db: TurriDB = request.app.state.db
        success, failures = await update_customer_profiles_based_on_analytics(
            db, from_date_dt
        )
        return {
            "status": "success",
            "message": f"Customer profiles updated from analytics. Success: {success}, Failures: {failures}",
            "success": success,
            "failures": failures,
        }
    except Exception as e:
        logger.exception("Failed to update customer profiles from analytics")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
