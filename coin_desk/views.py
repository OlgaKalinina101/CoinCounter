"""
Views for coin_desk application.

Handles Bitrix24 webhooks for deals and leads,
and provides deal statistics endpoints.
"""
import logging
from typing import Type, Dict

from dateutil.parser import parse
from django.db.models import Count, Model
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from coin_counter import settings
from .models import Deal, Lead

logger = logging.getLogger('coin_desk')


# ==============================================================================
# ОБЩАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ WEBHOOKS
# ==============================================================================

def process_bitrix_webhook(
    request,
    model_class: Type[Model],
    token: str,
    id_field_name: str,
    status_field_name: str,
    event_prefix: str
) -> JsonResponse:
    """
    Универсальная обработка webhook от Битрикс24.
    
    Args:
        request: HTTP request
        model_class: Модель (Deal или Lead)
        token: Токен для проверки
        id_field_name: Имя поля ID в данных ('deal_id' или 'lead_id')
        status_field_name: Имя поля статуса ('stage_id' или 'status_id')
        event_prefix: Префикс события ('ONCRMDEAL' или 'ONCRMLEAD')
    
    Returns:
        JsonResponse с результатом обработки
    """
    logger.info(f"Request method: {request.method}, Headers: {request.headers}")
    
    if request.method != 'POST':
        return JsonResponse({'status': 'method not allowed'}, status=405)
    
    try:
        # Проверяем Content-Type
        content_type = request.headers.get('Content-Type', '')
        if 'application/x-www-form-urlencoded' not in content_type:
            logger.error(f"Invalid Content-Type: {content_type}")
            return JsonResponse(
                {'status': 'error', 'error': 'Expected application/x-www-form-urlencoded'}, 
                status=400
            )
        
        # Парсим данные из POST
        data = request.POST
        logger.info(f"Parsed data: {dict(data)}")
        
        # Проверяем токен
        received_token = data.get('auth[application_token]')
        if received_token != token:
            logger.error(f"Invalid token: received={received_token}, expected={token}")
            return JsonResponse({'status': 'invalid token'}, status=403)
        
        # Извлекаем поля события
        event = data.get('event')
        object_id = data.get('data[FIELDS][ID]')
        status_value = data.get(f'data[FIELDS][{status_field_name.upper()}]')
        date_modify = data.get('data[FIELDS][DATE_MODIFY]')
        
        # Проверяем обязательные поля
        if not event or not object_id:
            logger.error(f"Missing required fields: event={event}, {id_field_name}={object_id}")
            return JsonResponse(
                {'status': 'error', 'error': f'Missing event or {id_field_name}'}, 
                status=400
            )
        
        # Обработка DELETE
        if event == f'{event_prefix}DELETE':
            model_class.objects.filter(**{id_field_name: object_id}).delete()
            logger.info(f"Deleted {model_class.__name__}: {object_id}")
            return JsonResponse({'status': 'success'}, status=200)
        
        # Обработка ADD и UPDATE
        if event in [f'{event_prefix}ADD', f'{event_prefix}UPDATE']:
            status_value = status_value or 'UNKNOWN'
            
            # Парсинг даты
            if not date_modify:
                logger.warning(f"Missing date_modify for {id_field_name}={object_id}, using current time")
                modify_date = timezone.now()
            else:
                try:
                    modify_date = parse(date_modify)
                    if not timezone.is_aware(modify_date):
                        modify_date = timezone.make_aware(modify_date)
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid date format for {id_field_name}={object_id}: {date_modify}, error: {str(e)}")
                    return JsonResponse({'status': 'error', 'error': 'Invalid date format'}, status=400)
            
            # Сохранение
            model_class.objects.update_or_create(
                **{id_field_name: object_id},
                defaults={
                    status_field_name: status_value,
                    'date_modify': modify_date,
                }
            )
            action = 'Created' if event == f'{event_prefix}ADD' else 'Updated'
            logger.info(f"{action} {model_class.__name__}: {object_id}, {status_field_name}={status_value}")
            return JsonResponse({'status': 'success'}, status=200)
        
        # Неизвестное событие
        logger.error(f"Unknown event: {event}")
        return JsonResponse({'status': 'error', 'error': f'Unknown event: {event}'}, status=400)
    
    except Exception as e:
        logger.error(f"Unexpected error for {model_class.__name__} webhook: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# ==============================================================================
# WEBHOOK HANDLERS
# ==============================================================================

@csrf_exempt
def webhook_handler(request):
    """Webhook для обработки сделок (Deals) из Битрикс24"""
    return process_bitrix_webhook(
        request=request,
        model_class=Deal,
        token=settings.WEBHOOK_TOKEN,
        id_field_name='deal_id',
        status_field_name='stage_id',
        event_prefix='ONCRMDEAL'
    )


# ==============================================================================
# DEAL STATS - общая логика
# ==============================================================================

def get_deal_stats(year: int = None, month: int = None) -> Dict[str, int]:
    """
    Получает статистику по сделкам за указанный период.
    
    Args:
        year: Год (по умолчанию текущий)
        month: Месяц (по умолчанию текущий)
    
    Returns:
        Dict с ключами 'successful_deals' и 'failed_deals'
    """
    now = timezone.now()
    year = year or now.year
    month = month or now.month
    
    stats = Deal.objects.filter(
        date_modify__year=year,
        date_modify__month=month,
        stage_id__in=['WON', 'LOSE']
    ).values('stage_id').annotate(count=Count('stage_id'))
    
    result = {'successful_deals': 0, 'failed_deals': 0}
    for stat in stats:
        if stat['stage_id'] == 'WON':
            result['successful_deals'] = stat['count']
        elif stat['stage_id'] == 'LOSE':
            result['failed_deals'] = stat['count']
    
    return result


def deal_stats_view(request):
    """JSON-ответ для API с статистикой по сделкам"""
    year = int(request.GET.get('year')) if request.GET.get('year') else None
    month = int(request.GET.get('month')) if request.GET.get('month') else None
    result = get_deal_stats(year, month)
    return JsonResponse(result)


def deal_stats_table(request):
    """HTML-таблица со статистикой по сделкам"""
    year = int(request.GET.get('year')) if request.GET.get('year') else None
    month = int(request.GET.get('month')) if request.GET.get('month') else None
    stats = get_deal_stats(year, month)
    return render(request, 'coin_desk/stats_table.html', stats)


@csrf_exempt
def webhook_handler_2(request):
    """Webhook для обработки лидов (Leads) из Битрикс24"""
    return process_bitrix_webhook(
        request=request,
        model_class=Lead,
        token=settings.WEBHOOK_TOKEN_2,
        id_field_name='lead_id',
        status_field_name='status_id',
        event_prefix='ONCRMLEAD'
    )