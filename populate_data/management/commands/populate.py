import os
import random
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

fake = Faker()

# Default password for all generated users
DEFAULT_PASSWORD = 'Pass1234!'

# Uzbek phone prefix
UZ_PHONE_PREFIX = '+99890'

# Uzbekistan-specific data
UZ_REGIONS_CITIES = {
    'Tashkent Region': ['Tashkent', 'Chirchik', 'Olmaliq', 'Angren'],
    'Samarkand Region': ['Samarkand', 'Kattakurgan', 'Urgut'],
    'Bukhara Region': ['Bukhara', 'Kogon', 'Gijduvan'],
    'Fergana Region': ['Fergana', 'Margilan', 'Quvasoy'],
    'Andijan Region': ['Andijan', 'Asaka', 'Shahrixon'],
    'Namangan Region': ['Namangan', 'Chust', 'Pop'],
    'Kashkadarya Region': ['Karshi', 'Shahrisabz', 'Kitob'],
    'Surkhandarya Region': ['Termez', 'Denov', 'Boysun'],
    'Khorezm Region': ['Urgench', 'Khiva'],
    'Navoi Region': ['Navoi', 'Zarafshan'],
    'Jizzakh Region': ['Jizzakh', 'Gagarin'],
    'Syrdarya Region': ['Guliston', 'Sirdaryo'],
    'Karakalpakstan': ['Nukus', 'Kungrad'],
}

UZ_FIRST_NAMES_MALE = [
    'Alisher', 'Bekzod', 'Doniyor', 'Eldor', 'Farhod', 'Jasur', 'Kamoliddin',
    'Laziz', 'Mansur', 'Nodir', 'Otabek', 'Rustam', 'Sardor', 'Tahir', 'Ulugbek',
    'Vohid', 'Xurshid', 'Yoqub', 'Zafar', 'Amir', 'Bobur', 'Islom', 'Mirzo',
    'Sherzod', 'Abdulla', 'Behruz', 'Dilshod', 'Erkin', 'Hamid', 'Ilhom',
]

UZ_FIRST_NAMES_FEMALE = [
    'Aziza', 'Barno', 'Dildora', 'Feruza', 'Gulnora', 'Hulkar', 'Iroda',
    'Kamola', 'Lola', 'Madina', 'Nargiza', 'Ozoda', 'Parvina', 'Qunduz',
    'Rohila', 'Sabohat', 'Tahira', 'Umida', 'Venera', 'Xilola', 'Yulduz',
    'Zulfiya', 'Adolat', 'Baxtigul', 'Dilorom', 'Farida', 'Gavhar', 'Nilufar',
]

UZ_LAST_NAMES = [
    'Karimov', 'Aliyev', 'Mirzayev', 'Toshmatov', 'Umarov', 'Botirov',
    'Djuraev', 'Ergashev', 'Fozilov', 'Gafurov', 'Hamidov', 'Ibragimov',
    'Jalolov', 'Komilov', 'Latipov', 'Mahmudov', 'Nazarov', 'Olimov',
    'Pardayev', 'Qodirov', 'Rahimov', 'Salimov', 'Turgunov', 'Usmonov',
    'Valiyev', 'Xasanov', 'Yusupov', 'Zakirov', 'Abdullayev', 'Bakiyev',
]

PRODUCTS = [
    # Hardware — physical POS devices sold to merchants
    {'code': 'POS-TERM', 'name': 'POS Terminal', 'category': 'Hardware'},
    {'code': 'POS-MINI', 'name': 'Mini Card Reader', 'category': 'Hardware'},
    # Subscription — monthly payment processing plans
    {'code': 'PAY-STD', 'name': 'Payment Processing Standard', 'category': 'Subscription'},
    {'code': 'PAY-PRO', 'name': 'Payment Processing Pro', 'category': 'Subscription'},
    # Service — one-time services
    {'code': 'SVC-INST', 'name': 'Installation & Setup', 'category': 'Service'},
]

INTERACTION_TYPES = ['Phone', 'Email', 'In Person', 'Online Chat', 'Referral', 'Walk-in', 'Social Media']


def uz_phone():
    return f'+99890{random.randint(1000000, 9999999)}'


def uz_full_name():
    if random.random() < 0.5:
        first = random.choice(UZ_FIRST_NAMES_MALE)
    else:
        first = random.choice(UZ_FIRST_NAMES_FEMALE)
    last = random.choice(UZ_LAST_NAMES)
    return f'{first} {last}', first, last


def _force_dates(model_class, pk, created_at=None, updated_at=None):
    """
    Force-set auto_now_add / auto_now fields by using QuerySet.update(),
    which bypasses Django's auto_now/auto_now_add behavior.
    """
    update_kwargs = {}
    if created_at is not None:
        update_kwargs['created_at'] = created_at
    if updated_at is not None:
        update_kwargs['updated_at'] = updated_at
    if update_kwargs:
        model_class.objects.filter(pk=pk).update(**update_kwargs)


def _random_datetime(now, days_ago_max, days_ago_min=0):
    """Generate a random datetime between days_ago_min and days_ago_max before now."""
    days_ago = random.randint(days_ago_min, days_ago_max)
    return now - datetime.timedelta(
        days=days_ago,
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )


class Command(BaseCommand):
    help = (
        'Populate the database with realistic random data using Faker.\n'
        'Creates tenants, users with roles, leads, sales, bonuses, and KPIs.\n'
        'Generates a credentials.txt file with all login info and hierarchy.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenants', type=int, default=1,
            help='Number of tenants to create (default: 1)',
        )
        parser.add_argument(
            '--agents-per-supervisor', type=int, default=4,
            help='Number of agents per supervisor (default: 4)',
        )
        parser.add_argument(
            '--supervisors', type=int, default=3,
            help='Number of supervisors per tenant (default: 3)',
        )
        parser.add_argument(
            '--customers', type=int, default=80,
            help='Number of customers per tenant (default: 80)',
        )
        parser.add_argument(
            '--leads', type=int, default=200,
            help='Number of leads per tenant (default: 200)',
        )
        parser.add_argument(
            '--sales', type=int, default=60,
            help='Number of sales per tenant (default: 60)',
        )
        parser.add_argument(
            '--kpi-days', type=int, default=90,
            help='Number of days of KPI history (default: 90)',
        )
        parser.add_argument(
            '--output', type=str, default='credentials.txt',
            help='Output file for credentials (default: credentials.txt)',
        )
        parser.add_argument(
            '--flush', action='store_true',
            help='Delete ALL existing data before populating',
        )

    def handle(self, *args, **options):
        from tenancy.models import (
            Tenant, Region, City, Product, Customer, Agent,
            SubscriptionPlan, Subscription, Payment,
        )
        from users.models import User, Role, UserRole
        from leads.models import LeadPipeline, LeadStage, Lead, LeadApplication, LeadStageHistory
        from conversions.models import Sale
        from bonuses.models import BonusRule, CommissionPolicy
        from analytics.models import KPIAgentDaily

        num_tenants = options['tenants']
        num_supervisors = options['supervisors']
        agents_per_sup = options['agents_per_supervisor']
        num_customers = options['customers']
        num_leads = options['leads']
        num_sales = options['sales']
        kpi_days = options['kpi_days']
        output_file = options['output']

        if options['flush']:
            self.stdout.write(self.style.WARNING('Flushing all existing data...'))
            KPIAgentDaily.objects.all().delete()
            Sale.objects.all().delete()
            LeadStageHistory.objects.all().delete()
            LeadApplication.objects.all().delete()
            Lead.objects.all().delete()
            LeadStage.objects.all().delete()
            LeadPipeline.objects.all().delete()
            BonusRule.objects.all().delete()
            CommissionPolicy.objects.all().delete()
            Customer.objects.all().delete()
            Agent.objects.all().delete()
            UserRole.objects.all().delete()
            Payment.objects.all().delete()
            Subscription.objects.all().delete()
            SubscriptionPlan.objects.all().delete()
            City.objects.all().delete()
            Region.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            Tenant.objects.all().delete()
            Role.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  All data flushed.'))

        # Collect all credentials for the output file
        credentials_report = []
        now = timezone.now()

        # ── Roles ──────────────────────────────────────────────
        self.stdout.write('Creating roles...')
        roles_data = [
            {'code': 'ADMIN', 'name': 'Administrator', 'color': '#EF4444', 'icon': 'shield',
             'permissions': {'users': ['view', 'create', 'update', 'delete'],
                             'leads': ['view', 'create', 'update', 'delete'],
                             'products': ['view', 'create', 'update', 'delete'],
                             'bonuses': ['view', 'create', 'update', 'delete'],
                             'analytics': ['view'], 'tenancy': ['view', 'update']}},
            {'code': 'MANAGER', 'name': 'Manager', 'color': '#8B5CF6', 'icon': 'briefcase',
             'permissions': {'users': ['view', 'create', 'update'],
                             'leads': ['view', 'create', 'update'],
                             'products': ['view', 'create', 'update'],
                             'bonuses': ['view', 'update'],
                             'analytics': ['view']}},
            {'code': 'SUPERVISOR', 'name': 'Supervisor', 'color': '#3B82F6', 'icon': 'users',
             'permissions': {'users': ['view'],
                             'leads': ['view', 'create', 'update'],
                             'products': ['view'],
                             'analytics': ['view']}},
            {'code': 'AGENT', 'name': 'Agent', 'color': '#10B981', 'icon': 'user',
             'permissions': {'leads': ['view', 'create', 'update'],
                             'analytics': ['view']}},
            {'code': 'FINANCE', 'name': 'Accountant', 'color': '#F59E0B', 'icon': 'calculator',
             'permissions': {'bonuses': ['view', 'update'],
                             'analytics': ['view'],
                             'users': ['view']}},
        ]
        roles = {}
        for rd in roles_data:
            role, _ = Role.objects.update_or_create(code=rd['code'], defaults=rd)
            roles[rd['code']] = role
        self.stdout.write(self.style.SUCCESS(f'  {len(roles)} roles ready'))

        # ── Subscription Plans ─────────────────────────────────
        self.stdout.write('Creating subscription plans...')
        plans_data = [
            {'name': 'Starter', 'price': Decimal('29.00'), 'max_agents': 5,
             'storage_limit': '1 GB',
             'description': 'Perfect for small teams getting started',
             'features': ['Lead Tracking', 'Basic Analytics']},
            {'name': 'Professional', 'price': Decimal('99.00'), 'max_agents': 50,
             'storage_limit': '10 GB',
             'description': 'Full-featured plan for growing teams',
             'features': ['Lead Tracking', 'KPI Analytics', 'Bonus Engine', 'Team Management']},
            {'name': 'Enterprise', 'price': Decimal('299.00'), 'max_agents': 500,
             'storage_limit': '100 GB',
             'description': 'Unlimited power for large organizations',
             'features': ['Lead Tracking', 'KPI Analytics', 'Bonus Engine',
                          'Team Management', 'API Access', 'Custom Reports', 'Priority Support']},
        ]
        plan_objs = []
        for pd in plans_data:
            plan, _ = SubscriptionPlan.objects.update_or_create(
                name=pd.pop('name'), defaults={**pd, 'is_active': True}
            )
            plan_objs.append(plan)
        self.stdout.write(self.style.SUCCESS(f'  {len(plan_objs)} subscription plans ready'))

        # ── Generate per-tenant data ──────────────────────────
        company_names = [
            ('Brother Corp', 'brother-corp'),
            ('Silk Road Trading', 'silk-road'),
            ('Samarkand Solutions', 'samarkand-sol'),
            ('Tashkent Digital', 'tashkent-dig'),
            ('Fergana Valley Tech', 'fergana-tech'),
        ]

        for t_idx in range(num_tenants):
            if t_idx < len(company_names):
                tenant_name, tenant_code = company_names[t_idx]
            else:
                tenant_name = fake.company()
                tenant_code = fake.slug()[:20]

            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Tenant {t_idx + 1}/{num_tenants}: {tenant_name}')
            self.stdout.write(f'{"="*60}')

            tenant_report = {
                'tenant_name': tenant_name,
                'tenant_code': tenant_code,
                'admin': None,
                'managers': [],
                'finance': [],
                'supervisors': [],
                'agents': [],
            }

            # ── Tenant ─────────────────────────────────────────
            # Tenant was "founded" 6-18 months ago
            tenant_created_at = _random_datetime(now, days_ago_max=540, days_ago_min=180)

            tenant, _ = Tenant.objects.update_or_create(
                code=tenant_code,
                defaults={'name': tenant_name, 'is_active': True}
            )
            _force_dates(Tenant, tenant.pk,
                         created_at=tenant_created_at, updated_at=tenant_created_at)

            # ── Subscription ───────────────────────────────────
            chosen_plan = plan_objs[1]  # Professional
            sub_created_at = tenant_created_at + datetime.timedelta(
                minutes=random.randint(1, 60))

            sub, _ = Subscription.objects.update_or_create(
                tenant=tenant,
                defaults={
                    'plan': chosen_plan,
                    'status': 'active',
                    'current_period_start': now - datetime.timedelta(days=random.randint(0, 29)),
                    'current_period_end': now + datetime.timedelta(days=random.randint(1, 30)),
                }
            )
            _force_dates(Subscription, sub.pk,
                         created_at=sub_created_at, updated_at=sub_created_at)

            # ── Payment history ────────────────────────────────
            for m in range(3):
                payment_date = now - datetime.timedelta(days=30 * (m + 1))
                pay = Payment.objects.create(
                    tenant=tenant,
                    subscription=sub,
                    amount=chosen_plan.price,
                    status='completed',
                    card_brand=random.choice(['Visa', 'MasterCard', 'Humo', 'UzCard']),
                    card_first4=str(random.randint(4000, 5999)),
                    card_last4=str(random.randint(1000, 9999)),
                    cardholder_name=tenant_name,
                    billing_email=f'billing@{tenant_code}.uz',
                    currency='USD',
                )
                _force_dates(Payment, pay.pk,
                             created_at=payment_date, updated_at=payment_date)

            # ── Regions & Cities ───────────────────────────────
            self.stdout.write('  Creating regions & cities...')
            selected_regions = dict(random.sample(
                list(UZ_REGIONS_CITIES.items()),
                min(6, len(UZ_REGIONS_CITIES))
            ))
            region_objs = {}
            city_objs = {}
            # Regions/cities created when tenant was set up
            setup_date = tenant_created_at + datetime.timedelta(hours=random.randint(1, 24))

            for rname, cities in selected_regions.items():
                region, _ = Region.objects.update_or_create(
                    tenant=tenant, name=rname,
                    defaults={'code': rname[:3].upper(), 'is_active': True}
                )
                _force_dates(Region, region.pk,
                             created_at=setup_date, updated_at=setup_date)
                region_objs[rname] = region
                for cname in cities:
                    city, _ = City.objects.update_or_create(
                        tenant=tenant, region=region, name=cname,
                        defaults={'code': cname[:3].upper(), 'is_active': True}
                    )
                    _force_dates(City, city.pk,
                                 created_at=setup_date, updated_at=setup_date)
                    city_objs[cname] = city
            self.stdout.write(self.style.SUCCESS(
                f'    {len(region_objs)} regions, {len(city_objs)} cities'))

            # ── Products ───────────────────────────────────────
            self.stdout.write('  Creating products...')
            product_objs = []
            product_setup_date = setup_date + datetime.timedelta(hours=random.randint(1, 12))
            for pd in PRODUCTS:
                prod, _ = Product.objects.update_or_create(
                    tenant=tenant, code=pd['code'],
                    defaults={'name': pd['name'], 'category': pd['category'], 'is_active': True}
                )
                _force_dates(Product, prod.pk,
                             created_at=product_setup_date, updated_at=product_setup_date)
                product_objs.append(prod)
            self.stdout.write(self.style.SUCCESS(f'    {len(product_objs)} products'))

            all_region_names = list(region_objs.keys())
            used_phones = set()
            agent_counter = 0

            def _unique_phone():
                while True:
                    p = uz_phone()
                    if p not in used_phones:
                        used_phones.add(p)
                        return p

            def _create_user_and_agent(username, full_name, email, phone,
                                       role_code, region_name, city_name, agent_code,
                                       parent_agent=None, user_created_at=None):
                if user_created_at is None:
                    user_created_at = _random_datetime(now, days_ago_max=300, days_ago_min=30)

                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        'full_name': full_name,
                        'email': email,
                        'phone_number': phone,
                        'tenant': tenant,
                        'is_active': True,
                        'is_staff': role_code in ('ADMIN', 'MANAGER'),
                        'is_superuser': role_code == 'ADMIN',
                    }
                )
                if created:
                    user.set_password(DEFAULT_PASSWORD)
                    user.save()

                # Force user dates
                _force_dates(User, user.pk,
                             created_at=user_created_at, updated_at=user_created_at)

                # UserRole assigned_at
                ur, _ = UserRole.objects.update_or_create(
                    tenant=tenant, user=user, role=roles[role_code]
                )
                UserRole.objects.filter(pk=ur.pk).update(
                    assigned_at=user_created_at + datetime.timedelta(minutes=random.randint(1, 30)))

                hired_at = user_created_at.date() - datetime.timedelta(
                    days=random.randint(0, 60))
                agent, _ = Agent.objects.update_or_create(
                    tenant=tenant, agent_code=agent_code,
                    defaults={
                        'user': user,
                        'region': region_objs[region_name],
                        'city': city_objs[city_name],
                        'parent': parent_agent,
                        'hired_at': hired_at,
                        'status': 'active',
                    }
                )
                _force_dates(Agent, agent.pk,
                             created_at=user_created_at, updated_at=user_created_at)

                return user, agent

            # ── Admin ──────────────────────────────────────────
            self.stdout.write('  Creating admin...')
            admin_full, admin_first, admin_last = uz_full_name()
            admin_username = f'{admin_first.lower()}_{tenant_code.replace("-", "")[:6]}'
            admin_email = f'{admin_first.lower()}@{tenant_code}.uz'
            admin_phone = _unique_phone()
            r_name = all_region_names[0]
            c_name = list(selected_regions[r_name])[0]

            # Admin created right after tenant
            admin_created = tenant_created_at + datetime.timedelta(
                minutes=random.randint(5, 120))
            admin_user, admin_agent = _create_user_and_agent(
                admin_username, admin_full, admin_email, admin_phone,
                'ADMIN', r_name, c_name, f'{tenant_code[:4].upper()}-ADM-001',
                user_created_at=admin_created
            )
            tenant_report['admin'] = {
                'username': admin_username, 'full_name': admin_full,
                'email': admin_email, 'phone': admin_phone, 'role': 'Administrator',
            }
            self.stdout.write(self.style.SUCCESS(f'    Admin: {admin_full} ({admin_username})'))

            # ── Manager ────────────────────────────────────────
            self.stdout.write('  Creating manager...')
            mgr_full, mgr_first, mgr_last = uz_full_name()
            mgr_username = f'{mgr_first.lower()}_{tenant_code.replace("-", "")[:6]}_mgr'
            mgr_email = f'{mgr_first.lower()}.mgr@{tenant_code}.uz'
            mgr_phone = _unique_phone()

            # Manager joined shortly after admin
            mgr_created = admin_created + datetime.timedelta(
                days=random.randint(1, 14), hours=random.randint(0, 23))
            mgr_user, mgr_agent = _create_user_and_agent(
                mgr_username, mgr_full, mgr_email, mgr_phone,
                'MANAGER', r_name, c_name, f'{tenant_code[:4].upper()}-MGR-001',
                user_created_at=mgr_created
            )
            tenant_report['managers'].append({
                'username': mgr_username, 'full_name': mgr_full,
                'email': mgr_email, 'phone': mgr_phone, 'role': 'Manager',
            })
            self.stdout.write(self.style.SUCCESS(f'    Manager: {mgr_full} ({mgr_username})'))

            # ── Finance / Accountant ───────────────────────────
            self.stdout.write('  Creating accountant...')
            fin_full, fin_first, fin_last = uz_full_name()
            fin_username = f'{fin_first.lower()}_{tenant_code.replace("-", "")[:6]}_fin'
            fin_email = f'{fin_first.lower()}.fin@{tenant_code}.uz'
            fin_phone = _unique_phone()

            fin_created = admin_created + datetime.timedelta(
                days=random.randint(3, 21), hours=random.randint(0, 23))
            fin_user, fin_agent = _create_user_and_agent(
                fin_username, fin_full, fin_email, fin_phone,
                'FINANCE', r_name, c_name, f'{tenant_code[:4].upper()}-FIN-001',
                user_created_at=fin_created
            )
            tenant_report['finance'].append({
                'username': fin_username, 'full_name': fin_full,
                'email': fin_email, 'phone': fin_phone, 'role': 'Accountant',
            })
            self.stdout.write(self.style.SUCCESS(f'    Accountant: {fin_full} ({fin_username})'))

            # ── Supervisors & Agents ───────────────────────────
            self.stdout.write('  Creating supervisors & agents...')
            supervisor_agents = []
            all_field_agents = []

            for s_idx in range(num_supervisors):
                sup_full, sup_first, sup_last = uz_full_name()
                sup_username = f'{sup_first.lower()}_{tenant_code.replace("-", "")[:6]}_sup{s_idx + 1}'
                sup_email = f'{sup_first.lower()}.sup{s_idx + 1}@{tenant_code}.uz'
                sup_phone = _unique_phone()
                sup_region = all_region_names[s_idx % len(all_region_names)]
                sup_city = selected_regions[sup_region][0]

                # Supervisors joined after manager, staggered
                sup_created = mgr_created + datetime.timedelta(
                    days=random.randint(1, 30) + s_idx * 7,
                    hours=random.randint(0, 23))

                sup_user, sup_agent = _create_user_and_agent(
                    sup_username, sup_full, sup_email, sup_phone,
                    'SUPERVISOR', sup_region, sup_city,
                    f'{tenant_code[:4].upper()}-SUP-{s_idx + 1:03d}',
                    user_created_at=sup_created
                )
                supervisor_agents.append(sup_agent)

                sup_report = {
                    'username': sup_username, 'full_name': sup_full,
                    'email': sup_email, 'phone': sup_phone,
                    'role': 'Supervisor', 'region': sup_region,
                    'agents': [],
                }

                # Create agents under this supervisor
                for a_idx in range(agents_per_sup):
                    agent_counter += 1
                    ag_full, ag_first, ag_last = uz_full_name()
                    ag_username = f'{ag_first.lower()}_{tenant_code.replace("-", "")[:6]}_ag{agent_counter}'
                    ag_email = f'{ag_first.lower()}.ag{agent_counter}@{tenant_code}.uz'
                    ag_phone = _unique_phone()
                    ag_region = sup_region
                    ag_city = random.choice(selected_regions[ag_region])

                    # Agents joined after their supervisor, staggered
                    ag_created = sup_created + datetime.timedelta(
                        days=random.randint(3, 45) + a_idx * 5,
                        hours=random.randint(0, 23))
                    # Don't let agent creation go past "now"
                    if ag_created > now:
                        ag_created = now - datetime.timedelta(
                            days=random.randint(1, 30))

                    ag_user, ag_agent = _create_user_and_agent(
                        ag_username, ag_full, ag_email, ag_phone,
                        'AGENT', ag_region, ag_city,
                        f'{tenant_code[:4].upper()}-AG-{agent_counter:03d}',
                        parent_agent=sup_agent,
                        user_created_at=ag_created
                    )
                    all_field_agents.append(ag_agent)

                    sup_report['agents'].append({
                        'username': ag_username, 'full_name': ag_full,
                        'email': ag_email, 'phone': ag_phone, 'role': 'Agent',
                        'city': ag_city,
                    })

                tenant_report['supervisors'].append(sup_report)
                self.stdout.write(self.style.SUCCESS(
                    f'    Supervisor: {sup_full} ({sup_username}) '
                    f'with {agents_per_sup} agents in {sup_region}'))

            # ── Lead Pipelines & Stages ────────────────────────
            self.stdout.write('  Creating pipelines & stages...')
            pipeline_definitions = {
                # POS Terminal — full hardware sales cycle with demo
                'POS-TERM': [
                    ('New Lead', 1, False),
                    ('Contacted', 2, False),
                    ('Demo Scheduled', 3, False),
                    ('Demo Done', 4, False),
                    ('Proposal Sent', 5, False),
                    ('Negotiation', 6, False),
                    ('Closed Won', 7, True),
                    ('Closed Lost', 8, True),
                ],
                # Mini Card Reader — shorter cycle, simpler product
                'POS-MINI': [
                    ('New Lead', 1, False),
                    ('Contacted', 2, False),
                    ('Quote Sent', 3, False),
                    ('Closed Won', 4, True),
                    ('Closed Lost', 5, True),
                ],
                # Payment Processing Standard — subscription with trial
                'PAY-STD': [
                    ('New Lead', 1, False),
                    ('Contacted', 2, False),
                    ('Trial Started', 3, False),
                    ('Trial Review', 4, False),
                    ('Closed Won', 5, True),
                    ('Closed Lost', 6, True),
                ],
                # Payment Processing Pro — longer subscription cycle
                'PAY-PRO': [
                    ('New Lead', 1, False),
                    ('Qualification', 2, False),
                    ('Needs Analysis', 3, False),
                    ('Trial Started', 4, False),
                    ('Proposal', 5, False),
                    ('Contract Review', 6, False),
                    ('Closed Won', 7, True),
                    ('Closed Lost', 8, True),
                ],
                # Installation & Setup — simple service fulfillment
                'SVC-INST': [
                    ('Requested', 1, False),
                    ('Scheduled', 2, False),
                    ('In Progress', 3, False),
                    ('Completed', 4, True),
                    ('Cancelled', 5, True),
                ],
            }

            pipelines = {}
            stages = {}
            pipeline_setup_date = product_setup_date + datetime.timedelta(
                hours=random.randint(1, 12))

            for prod in product_objs:
                if prod.code in pipeline_definitions:
                    pipeline, _ = LeadPipeline.objects.update_or_create(
                        tenant=tenant, product=prod, name=f'{prod.name} Pipeline',
                        defaults={'is_active': True}
                    )
                    _force_dates(LeadPipeline, pipeline.pk,
                                 created_at=pipeline_setup_date,
                                 updated_at=pipeline_setup_date)
                    pipelines[prod.id] = pipeline
                    for sname, sorder, is_terminal in pipeline_definitions[prod.code]:
                        stage, _ = LeadStage.objects.update_or_create(
                            tenant=tenant, pipeline=pipeline, stage_order=sorder,
                            defaults={'name': sname, 'is_terminal': is_terminal, 'is_active': True}
                        )
                        _force_dates(LeadStage, stage.pk,
                                     created_at=pipeline_setup_date,
                                     updated_at=pipeline_setup_date)
                        stages[(prod.id, sorder)] = stage
            self.stdout.write(self.style.SUCCESS(f'    {len(pipelines)} pipelines with stages'))

            # ── Customers ──────────────────────────────────────
            self.stdout.write('  Creating customers...')
            customer_objs = []
            for _ in range(num_customers):
                c_full, c_first, c_last = uz_full_name()
                cust_created = _random_datetime(now, days_ago_max=kpi_days, days_ago_min=0)
                cust, created = Customer.objects.get_or_create(
                    tenant=tenant,
                    phone=_unique_phone(),
                    defaults={'full_name': c_full}
                )
                if created:
                    _force_dates(Customer, cust.pk,
                                 created_at=cust_created, updated_at=cust_created)
                customer_objs.append(cust)
            self.stdout.write(self.style.SUCCESS(f'    {len(customer_objs)} customers'))

            # ── Leads & Applications ───────────────────────────
            self.stdout.write('  Creating leads...')
            lead_objs = []
            for _ in range(num_leads):
                agent = random.choice(all_field_agents)
                customer = random.choice(customer_objs)
                days_ago = random.randint(0, kpi_days)
                lead_created_at = now - datetime.timedelta(
                    days=days_ago, hours=random.randint(0, 23),
                    minutes=random.randint(0, 59))

                lead = Lead.objects.create(
                    tenant=tenant,
                    agent=agent,
                    customer=customer,
                    customer_name=customer.full_name,
                    customer_phone=customer.phone,
                    interaction_type=random.choice(INTERACTION_TYPES),
                    latitude=Decimal(str(round(random.uniform(37.5, 42.5), 6))),
                    longitude=Decimal(str(round(random.uniform(56.0, 71.0), 6))),
                    server_received_at=lead_created_at,
                )
                # Force lead dates to match the simulated creation time
                _force_dates(Lead, lead.pk,
                             created_at=lead_created_at, updated_at=lead_created_at)
                lead_objs.append(lead)

                # Create 1-2 lead applications per lead
                num_apps = random.choices([1, 2], weights=[80, 20])[0]
                prods_for_lead = random.sample(product_objs, min(num_apps, len(product_objs)))
                for i, prod in enumerate(prods_for_lead):
                    if prod.id in pipelines:
                        pipeline = pipelines[prod.id]
                        max_stage = max(o for (pid, o) in stages.keys() if pid == prod.id)
                        # Non-terminal stages are more likely for recent leads
                        if days_ago < 14:
                            stage_order = random.randint(1, max(1, max_stage - 2))
                        else:
                            stage_order = random.randint(1, max_stage)
                        stage = stages.get((prod.id, stage_order))
                        if stage:
                            app_created_at = lead_created_at + datetime.timedelta(
                                minutes=random.randint(1, 120))
                            status_updated = lead_created_at + datetime.timedelta(
                                hours=random.randint(1, 48))

                            app = LeadApplication.objects.create(
                                tenant=tenant,
                                lead=lead,
                                product=prod,
                                pipeline=pipeline,
                                current_stage=stage,
                                is_primary=(i == 0),
                                status_last_updated_at=status_updated,
                            )
                            _force_dates(LeadApplication, app.pk,
                                         created_at=app_created_at,
                                         updated_at=status_updated)

                            if i == 0:
                                lead.primary_application = app
                                lead.save(update_fields=['primary_application'])

                            # Create stage history
                            history_time = lead_created_at
                            for s_order in range(1, stage_order + 1):
                                from_s = stages.get((prod.id, s_order - 1))
                                to_s = stages.get((prod.id, s_order))
                                if to_s:
                                    history_time += datetime.timedelta(
                                        hours=random.randint(2, 72))
                                    LeadStageHistory.objects.create(
                                        tenant=tenant,
                                        lead=lead,
                                        lead_application=app,
                                        from_stage=from_s,
                                        to_stage=to_s,
                                        changed_at=history_time,
                                        note=fake.sentence() if random.random() < 0.3 else '',
                                    )
                            # Update last_stage_history on the app
                            last_hist = LeadStageHistory.objects.filter(
                                lead_application=app).order_by('-changed_at').first()
                            if last_hist:
                                app.last_stage_history = last_hist
                                app.save(update_fields=['last_stage_history'])

            self.stdout.write(self.style.SUCCESS(f'    {len(lead_objs)} leads with applications'))

            # ── Sales ──────────────────────────────────────────
            self.stdout.write('  Creating sales...')
            sale_count = 0
            for _ in range(num_sales):
                agent = random.choice(all_field_agents)
                customer = random.choice(customer_objs)
                prod = random.choice(product_objs)
                days_ago = random.randint(0, kpi_days)
                sold_at = now - datetime.timedelta(
                    days=days_ago, hours=random.randint(0, 23),
                    minutes=random.randint(0, 59))
                amount = Decimal(str(random.randint(500, 15000)))

                lead = Lead.objects.filter(
                    agent=agent, customer=customer, tenant=tenant
                ).first()
                lead_app = None
                if lead:
                    lead_app = LeadApplication.objects.filter(
                        lead=lead, product=prod
                    ).first()

                sale = Sale.objects.create(
                    tenant=tenant,
                    agent=agent,
                    customer=customer,
                    product=prod,
                    lead=lead,
                    lead_application=lead_app,
                    amount=amount,
                    status=random.choices(
                        ['completed', 'pending', 'cancelled'],
                        weights=[75, 15, 10]
                    )[0],
                    sold_at=sold_at,
                )
                # Force sale created_at to match sold_at
                _force_dates(Sale, sale.pk,
                             created_at=sold_at, updated_at=sold_at)
                sale_count += 1
            self.stdout.write(self.style.SUCCESS(f'    {sale_count} sales'))

            # ── Bonus Rules ────────────────────────────────────
            self.stdout.write('  Creating bonus rules...')
            bonus_created = tenant_created_at + datetime.timedelta(
                days=random.randint(7, 30))

            bonus_rules = [
                {
                    'name': 'High Value Sale Bonus',
                    'rule_dimension': 'SELL_AMOUNT',
                    'operator': 'GTE',
                    'num_from': Decimal('5000'),
                    'amount_type': 'percent_of_sale',
                    'amount_value': Decimal('15.0000'),
                    'cap_amount': Decimal('2000'),
                    'is_active': True,
                    'effective_from': tenant_created_at,
                },
                {
                    'name': 'Quick Conversion Bonus',
                    'rule_dimension': 'LEAD_TO_SELL_DELTA',
                    'operator': 'LTE',
                    'interval_from': datetime.timedelta(days=2),
                    'amount_type': 'fixed',
                    'amount_value': Decimal('150.0000'),
                    'is_active': True,
                    'effective_from': tenant_created_at,
                },
                {
                    'name': 'Premium Product Commission',
                    'rule_dimension': 'POTENTIAL_PRODUCT',
                    'operator': 'IN',
                    'text_values': 'POS-TERM, PAY-PRO',
                    'amount_type': 'percent_of_sale',
                    'amount_value': Decimal('12.0000'),
                    'cap_amount': Decimal('1500'),
                    'is_active': True,
                    'effective_from': tenant_created_at,
                },
                {
                    'name': 'New Agent Welcome Bonus',
                    'rule_dimension': 'USER_REG_TIME',
                    'operator': 'LTE',
                    'interval_from': datetime.timedelta(days=30),
                    'amount_type': 'fixed',
                    'amount_value': Decimal('50.0000'),
                    'is_active': True,
                    'effective_from': tenant_created_at + datetime.timedelta(days=30),
                },
                {
                    'name': 'Enterprise Deal Bonus',
                    'rule_dimension': 'SELL_AMOUNT',
                    'operator': 'GTE',
                    'num_from': Decimal('10000'),
                    'amount_type': 'percent_of_sale',
                    'amount_value': Decimal('20.0000'),
                    'cap_amount': Decimal('5000'),
                    'is_active': True,
                    'effective_from': tenant_created_at,
                },
            ]
            for br_data in bonus_rules:
                name = br_data.pop('name')
                br, _ = BonusRule.objects.update_or_create(
                    tenant=tenant, name=name, defaults=br_data
                )
                _force_dates(BonusRule, br.pk,
                             created_at=bonus_created, updated_at=bonus_created)
            self.stdout.write(self.style.SUCCESS(f'    {len(bonus_rules)} bonus rules'))

            # ── Commission Policy ──────────────────────────────
            cp, _ = CommissionPolicy.objects.update_or_create(
                tenant=tenant, name='Default Attribution Policy',
                defaults={
                    'mode': 'LAST_TOUCH',
                    'window_interval': datetime.timedelta(days=30),
                    'effective_from': tenant_created_at,
                    'is_active': True,
                }
            )
            _force_dates(CommissionPolicy, cp.pk,
                         created_at=bonus_created, updated_at=bonus_created)

            # ── KPI Agent Daily (derived from actual Leads & Sales) ─
            self.stdout.write('  Creating KPI daily records from real data...')
            kpi_count = 0

            # Build daily lead counts per agent from DB (not Python objects,
            # because _force_dates updates DB but not in-memory objects)
            from collections import defaultdict
            daily_leads = defaultdict(lambda: defaultdict(int))   # {agent_id: {date: count}}
            for lead in Lead.objects.filter(tenant=tenant).values('agent_id', 'created_at'):
                lead_date = lead['created_at'].date()
                daily_leads[lead['agent_id']][lead_date] += 1

            # Build daily sale counts & revenue per agent from actual Sale records
            daily_sales = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'revenue': Decimal('0')}))
            all_sales = Sale.objects.filter(tenant=tenant, status='completed')
            for sale in all_sales:
                sale_date = sale.sold_at.date() if sale.sold_at else sale.created_at.date()
                daily_sales[sale.agent_id][sale_date]['count'] += 1
                daily_sales[sale.agent_id][sale_date]['revenue'] += sale.amount

            # Collect all dates that have activity
            all_dates = set()
            for agent_dates in daily_leads.values():
                all_dates.update(agent_dates.keys())
            for agent_dates in daily_sales.values():
                all_dates.update(agent_dates.keys())

            for agent in all_field_agents:
                for kpi_date in sorted(all_dates):
                    leads_captured = daily_leads[agent.id].get(kpi_date, 0)
                    sale_info = daily_sales[agent.id].get(kpi_date, {'count': 0, 'revenue': Decimal('0')})
                    leads_converted = sale_info['count']
                    revenue = sale_info['revenue']

                    # Skip days with zero activity for this agent
                    if leads_captured == 0 and leads_converted == 0:
                        continue

                    conv_rate = Decimal(str(round(
                        leads_converted / max(leads_captured, 1) * 100, 2)))
                    bonus = Decimal(str(round(float(revenue) * random.uniform(0.08, 0.15), 2)))
                    net_profit = revenue - bonus

                    kpi_created_at = timezone.make_aware(
                        datetime.datetime.combine(
                            kpi_date, datetime.time(23, random.randint(0, 59), random.randint(0, 59))
                        )
                    )

                    kpi, _ = KPIAgentDaily.objects.update_or_create(
                        tenant=tenant, agent=agent, kpi_date=kpi_date,
                        defaults={
                            'leads_captured': leads_captured,
                            'leads_converted': leads_converted,
                            'conversion_rate': conv_rate,
                            'revenue_amount': revenue,
                            'bonus_amount': bonus,
                            'net_profit': net_profit,
                            'avg_time_to_convert': datetime.timedelta(
                                hours=random.randint(1, 96)),
                        }
                    )
                    KPIAgentDaily.objects.filter(pk=kpi.pk).update(
                        created_at=kpi_created_at)
                    kpi_count += 1
            self.stdout.write(self.style.SUCCESS(f'    {kpi_count} KPI daily records (from real leads & sales)'))

            credentials_report.append(tenant_report)

        # ── Generate credentials.txt ──────────────────────────
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))),
            output_file
        )
        self._write_credentials(output_path, credentials_report)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Population complete! Credentials saved to: {output_path}'))

    def _write_credentials(self, path, report):
        lines = []
        lines.append('=' * 70)
        lines.append('  POSightful — Populated Data Credentials')
        lines.append(f'  Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append(f'  Password for ALL users: {DEFAULT_PASSWORD}')
        lines.append('=' * 70)
        lines.append('')

        for t in report:
            lines.append('─' * 70)
            lines.append(f'  TENANT: {t["tenant_name"]}  (code: {t["tenant_code"]})')
            lines.append('─' * 70)
            lines.append('')

            # Admin
            a = t['admin']
            lines.append(f'  ★ ADMIN')
            lines.append(f'    Name     : {a["full_name"]}')
            lines.append(f'    Username : {a["username"]}')
            lines.append(f'    Email    : {a["email"]}')
            lines.append(f'    Phone    : {a["phone"]}')
            lines.append(f'    Password : {DEFAULT_PASSWORD}')
            lines.append('')

            # Managers
            for m in t['managers']:
                lines.append(f'  ★ MANAGER')
                lines.append(f'    Name     : {m["full_name"]}')
                lines.append(f'    Username : {m["username"]}')
                lines.append(f'    Email    : {m["email"]}')
                lines.append(f'    Phone    : {m["phone"]}')
                lines.append(f'    Password : {DEFAULT_PASSWORD}')
                lines.append('')

            # Finance
            for f in t['finance']:
                lines.append(f'  ★ ACCOUNTANT')
                lines.append(f'    Name     : {f["full_name"]}')
                lines.append(f'    Username : {f["username"]}')
                lines.append(f'    Email    : {f["email"]}')
                lines.append(f'    Phone    : {f["phone"]}')
                lines.append(f'    Password : {DEFAULT_PASSWORD}')
                lines.append('')

            # Supervisors with their agents
            for s in t['supervisors']:
                lines.append(f'  ★ SUPERVISOR — {s["region"]}')
                lines.append(f'    Name     : {s["full_name"]}')
                lines.append(f'    Username : {s["username"]}')
                lines.append(f'    Email    : {s["email"]}')
                lines.append(f'    Phone    : {s["phone"]}')
                lines.append(f'    Password : {DEFAULT_PASSWORD}')
                lines.append('')

                for ag in s['agents']:
                    lines.append(f'      ↳ AGENT — {ag["city"]}')
                    lines.append(f'        Name     : {ag["full_name"]}')
                    lines.append(f'        Username : {ag["username"]}')
                    lines.append(f'        Email    : {ag["email"]}')
                    lines.append(f'        Phone    : {ag["phone"]}')
                    lines.append(f'        Password : {DEFAULT_PASSWORD}')
                    lines.append('')

            lines.append('')

        lines.append('=' * 70)
        lines.append('  END OF CREDENTIALS')
        lines.append('=' * 70)
        lines.append('')

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
