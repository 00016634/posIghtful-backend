from django.db import migrations


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('tenancy', 'SubscriptionPlan')
    plans = [
        {
            'name': 'Starter',
            'price': 299,
            'description': 'Perfect for small teams getting started',
            'max_agents': 5,
            'storage_limit': '1 GB',
            'features': [
                'Up to 5 agents',
                'Basic analytics dashboard',
                'Lead management',
                'Email support',
                '1 GB storage',
            ],
        },
        {
            'name': 'Professional',
            'price': 799,
            'description': 'Best for growing sales organizations',
            'max_agents': 25,
            'storage_limit': '10 GB',
            'features': [
                'Up to 25 agents',
                'Advanced analytics & reports',
                'Lead & conversion tracking',
                'Bonus management',
                'Priority support',
                '10 GB storage',
                'Custom branding',
            ],
        },
        {
            'name': 'Enterprise',
            'price': 1999,
            'description': 'For large organizations with complex needs',
            'max_agents': 0,  # 0 = unlimited
            'storage_limit': 'Unlimited',
            'features': [
                'Unlimited agents',
                'Full analytics suite',
                'Advanced bonus rules engine',
                'Product funnel management',
                'Dedicated account manager',
                'Unlimited storage',
                'API access',
                'SSO & SAML',
            ],
        },
    ]
    for plan_data in plans:
        SubscriptionPlan.objects.update_or_create(
            name=plan_data['name'],
            defaults=plan_data,
        )


def reverse_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('tenancy', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(name__in=['Starter', 'Professional', 'Enterprise']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0003_subscriptionplan_subscription_payment'),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_plans),
    ]
