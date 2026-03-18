import logging
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

from conversions.models import Sale
from .models import BonusLedger
from .engine import evaluate_bonus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Sale)
def award_bonus_on_sale(sender, instance, created, **kwargs):
    """Award bonus when a Sale is created or updated with status 'completed'."""
    if instance.status != 'completed':
        return
    if BonusLedger.objects.filter(sale=instance).exists():
        return

    try:
        rule, amount, detail = evaluate_bonus(instance)
        BonusLedger.objects.create(
            tenant=instance.tenant,
            sale=instance,
            agent=instance.agent,
            rule=rule,
            bonus_amount=amount,
            calculation_detail=detail,
        )
        _update_agent_daily_kpi(instance, amount)
        logger.info("Bonus %s awarded for Sale #%s (rule: %s)", amount, instance.id, rule)
    except Exception:
        logger.exception("Failed to award bonus for Sale #%s", instance.id)


def _update_agent_daily_kpi(sale, bonus_amount):
    """Increment KPIAgentDaily counters for the sale's agent on the sale date."""
    from analytics.models import KPIAgentDaily

    kpi_date = sale.sold_at.date()
    obj, created = KPIAgentDaily.objects.get_or_create(
        tenant=sale.tenant,
        agent=sale.agent,
        kpi_date=kpi_date,
        defaults={
            'bonus_amount': bonus_amount,
            'revenue_amount': sale.amount,
            'leads_converted': 1,
        },
    )
    if not created:
        KPIAgentDaily.objects.filter(pk=obj.pk).update(
            bonus_amount=F('bonus_amount') + bonus_amount,
            revenue_amount=F('revenue_amount') + sale.amount,
            leads_converted=F('leads_converted') + 1,
        )
