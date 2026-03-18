from decimal import Decimal
from django.utils import timezone
from .models import BonusRule


def evaluate_bonus(sale):
    """
    Evaluate bonus rules against a completed sale.
    Returns (matched_rule, bonus_amount, calculation_detail).
    """
    now = timezone.now()
    rules = BonusRule.objects.filter(
        tenant=sale.tenant,
        is_active=True,
    ).order_by('id')

    for rule in rules:
        if rule.effective_from and rule.effective_from > now:
            continue
        if rule.effective_to and rule.effective_to < now:
            continue

        if _rule_matches(rule, sale):
            amount = _calculate_amount(rule, sale)
            detail = _build_detail(rule, sale, amount)
            return rule, amount, detail

    # Default fallback: 10% of sale amount
    amount = (sale.amount * Decimal('0.10')).quantize(Decimal('0.01'))
    detail = f"Default 10% of {sale.amount} = {amount}"
    return None, amount, detail


def _rule_matches(rule, sale):
    """Check if a rule's dimension + operator matches the sale."""
    dim = rule.rule_dimension
    op = rule.operator

    if dim == 'SELL_AMOUNT':
        return _compare_numeric(op, sale.amount, rule)

    if dim == 'POTENTIAL_PRODUCT' and sale.product:
        return _compare_text(op, sale.product.code, rule)

    if dim == 'LEAD_TO_SELL_DELTA' and sale.lead and sale.lead.created_at and sale.sold_at:
        delta = sale.sold_at - sale.lead.created_at
        return _compare_duration(op, delta, rule)

    if dim == 'SELL_TIME' and sale.sold_at:
        return _compare_timestamp(op, sale.sold_at, rule)

    if dim == 'LEAD_TIME' and sale.lead and sale.lead.created_at:
        return _compare_timestamp(op, sale.lead.created_at, rule)

    return False


def _compare_numeric(op, value, rule):
    """Compare a numeric value against rule's num_from/num_to."""
    value = Decimal(str(value))
    num_from = rule.num_from
    num_to = rule.num_to

    if op == 'EQ':
        return num_from is not None and value == num_from
    if op == 'NEQ':
        return num_from is not None and value != num_from
    if op == 'GT':
        return num_from is not None and value > num_from
    if op == 'GTE':
        return num_from is not None and value >= num_from
    if op == 'LT':
        return num_from is not None and value < num_from
    if op == 'LTE':
        return num_from is not None and value <= num_from
    if op == 'BETWEEN':
        return (num_from is not None and num_to is not None
                and num_from <= value <= num_to)
    return False


def _compare_text(op, value, rule):
    """Compare a text value against rule's text_value/text_values."""
    if op in ('IN', 'EQ'):
        values = [v.strip() for v in (rule.text_values or rule.text_value or '').split(',') if v.strip()]
        return value in values
    if op in ('NOT_IN', 'NEQ'):
        values = [v.strip() for v in (rule.text_values or rule.text_value or '').split(',') if v.strip()]
        return value not in values
    return False


def _compare_duration(op, delta, rule):
    """Compare a timedelta against rule's interval_from/interval_to."""
    interval_from = rule.interval_from
    interval_to = rule.interval_to

    if op == 'LT':
        return interval_from is not None and delta < interval_from
    if op == 'LTE':
        return interval_from is not None and delta <= interval_from
    if op == 'GT':
        return interval_from is not None and delta > interval_from
    if op == 'GTE':
        return interval_from is not None and delta >= interval_from
    if op == 'BETWEEN':
        return (interval_from is not None and interval_to is not None
                and interval_from <= delta <= interval_to)
    return False


def _compare_timestamp(op, value, rule):
    """Compare a datetime against rule's ts_from/ts_to."""
    ts_from = rule.ts_from
    ts_to = rule.ts_to

    if op == 'GT':
        return ts_from is not None and value > ts_from
    if op == 'GTE':
        return ts_from is not None and value >= ts_from
    if op == 'LT':
        return ts_from is not None and value < ts_from
    if op == 'LTE':
        return ts_from is not None and value <= ts_from
    if op == 'BETWEEN':
        return (ts_from is not None and ts_to is not None
                and ts_from <= value <= ts_to)
    return False


def _calculate_amount(rule, sale):
    """Calculate the bonus amount based on rule's amount_type."""
    if rule.amount_type == 'percent_of_sale':
        amount = (sale.amount * rule.amount_value / Decimal('100')).quantize(Decimal('0.01'))
        if rule.cap_amount and amount > rule.cap_amount:
            amount = rule.cap_amount
        return amount
    else:
        return rule.amount_value or Decimal('0')


def _build_detail(rule, sale, amount):
    """Build a human-readable calculation string."""
    if rule.amount_type == 'percent_of_sale':
        detail = f"{rule.amount_value}% of {sale.amount} = {amount}"
        if rule.cap_amount and (sale.amount * rule.amount_value / Decimal('100')) > rule.cap_amount:
            detail += f" (capped at {rule.cap_amount})"
        return detail
    return f"Fixed {rule.amount_value} bonus"
