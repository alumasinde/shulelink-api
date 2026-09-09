from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from app.core.config import settings
from app.core.database import get_pool_stats, ping_database
from app.core.rate_limit import limiter
router=APIRouter()
@router.get('/health',tags=['System'])
@limiter.limit('60/minute')
async def health(request:Request,response:Response):
    response.headers['Cache-Control']='no-store'
    return {'success':True,'data':{'service':settings.app_name,'version':settings.app_version,'status':'ok'}}
@router.get('/health/ready',tags=['System'])
@limiter.limit('30/minute')
async def readiness(request:Request,response:Response):
    database_ok=await ping_database();checks={'database':'ok' if database_ok else 'unavailable'}
    if database_ok:checks['database_pool']=get_pool_stats()
    status_code=200 if database_ok else 503
    return JSONResponse(status_code=status_code,content={'success':database_ok,'data':{'status':'ready' if database_ok else 'not_ready','checks':checks},'request_id':getattr(request.state,'request_id','unknown')},headers={'Cache-Control':'no-store'})
