from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    roles = [
        {
            'code': 'AGENT',
            'name': 'Agent',
            'description': 'Manage leads, track conversions, and view bonuses',
            'permissions': {
                'leads': ['view', 'create', 'update'],
                'conversions': ['view', 'create'],
                'bonuses': ['view'],
            },
            'color': 'blue',
            'icon': 'user',
        },
        {
            'code': 'SUPERVISOR',
            'name': 'Supervisor',
            'description': 'Monitor team performance and oversee leads',
            'permissions': {
                'leads': ['view', 'create', 'update', 'delete'],
                'agents': ['view', 'manage'],
                'analytics': ['view'],
            },
            'color': 'purple',
            'icon': 'users',
        },
        {
            'code': 'MANAGER',
            'name': 'Manager',
            'description': 'Organization analytics and policy configuration',
            'permissions': {
                'analytics': ['view'],
                'bonus_rules': ['view', 'create', 'update', 'delete'],
                'products': ['view', 'create', 'update'],
            },
            'color': 'green',
            'icon': 'building',
        },
        {
            'code': 'ACCOUNTANT',
            'name': 'Accountant',
            'description': 'Generate bonus reports and audit trails',
            'permissions': {
                'bonuses': ['view', 'export'],
                'reports': ['view', 'export'],
                'audit': ['view'],
            },
            'color': 'orange',
            'icon': 'receipt',
        },
        {
            'code': 'ADMIN',
            'name': 'Admin',
            'description': 'Manage users, products, and system settings',
            'permissions': {
                'users': ['view', 'create', 'update', 'delete'],
                'products': ['view', 'create', 'update', 'delete'],
                'system': ['view', 'configure'],
            },
            'color': 'red',
            'icon': 'shield',
        },
    ]
    for role_data in roles:
        Role.objects.update_or_create(
            code=role_data['code'],
            defaults=role_data,
        )


def reverse_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.filter(code__in=['AGENT', 'SUPERVISOR', 'MANAGER', 'ACCOUNTANT', 'ADMIN']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_role_color_role_icon_role_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_roles),
    ]
