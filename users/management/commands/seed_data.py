import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed the database with realistic sample data'

    def handle(self, *args, **options):
        from tenancy.models import (
            Tenant, Region, City, Product, Customer, Agent,
            SubscriptionPlan, Subscription,
        )
        from users.models import User, Role, UserRole
        from leads.models import LeadPipeline, LeadStage, Lead, LeadApplication
        from conversions.models import Sale
        from bonuses.models import BonusRule, CommissionPolicy
        from analytics.models import KPIAgentDaily

        self.stdout.write('Seeding database...')

        # ── Roles ──────────────────────────────────────────────
        roles_data = [
            {'code': 'ADMIN', 'name': 'Administrator', 'color': 'red', 'icon': 'shield',
             'permissions': {'users': ['view', 'create', 'update', 'delete'],
                             'leads': ['view', 'create', 'update', 'delete'],
                             'products': ['view', 'create', 'update', 'delete'],
                             'bonuses': ['view', 'create', 'update', 'delete'],
                             'analytics': ['view']}},
            {'code': 'MANAGER', 'name': 'Manager', 'color': 'purple', 'icon': 'briefcase',
             'permissions': {'users': ['view', 'create', 'update'],
                             'leads': ['view', 'create', 'update'],
                             'products': ['view', 'create', 'update'],
                             'bonuses': ['view', 'update'],
                             'analytics': ['view']}},
            {'code': 'SUPERVISOR', 'name': 'Supervisor', 'color': 'blue', 'icon': 'users',
             'permissions': {'users': ['view'],
                             'leads': ['view', 'create', 'update'],
                             'products': ['view'],
                             'analytics': ['view']}},
            {'code': 'AGENT', 'name': 'Agent', 'color': 'green', 'icon': 'user',
             'permissions': {'leads': ['view', 'create', 'update'],
                             'analytics': ['view']}},
            {'code': 'FINANCE', 'name': 'Accountant', 'color': 'orange', 'icon': 'calculator',
             'permissions': {'bonuses': ['view', 'update'],
                             'analytics': ['view'],
                             'users': ['view']}},
        ]
        roles = {}
        for rd in roles_data:
            role, _ = Role.objects.update_or_create(code=rd['code'], defaults=rd)
            roles[rd['code']] = role
        self.stdout.write(f'  Created {len(roles)} roles')

        # ── Subscription Plan ──────────────────────────────────
        plan, _ = SubscriptionPlan.objects.update_or_create(
            name='Professional',
            defaults={
                'price': Decimal('99.00'),
                'description': 'Full-featured plan for growing teams',
                'max_agents': 50,
                'storage_limit': '10 GB',
                'features': ['Lead Tracking', 'KPI Analytics', 'Bonus Engine', 'Team Management'],
                'is_active': True,
            }
        )

        # ── Tenant ─────────────────────────────────────────────
        tenant, _ = Tenant.objects.update_or_create(
            code='acme-insurance',
            defaults={'name': 'Acme Insurance Corp', 'is_active': True}
        )
        self.stdout.write(f'  Tenant: {tenant.name}')

        # Subscription
        Subscription.objects.update_or_create(
            tenant=tenant,
            defaults={
                'plan': plan,
                'status': 'active',
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + datetime.timedelta(days=30),
            }
        )

        # ── Regions & Cities ───────────────────────────────────
        regions_cities = {
            'North Region': ['Tashkent', 'Chirchik'],
            'South Region': ['Samarkand', 'Karshi'],
            'East Region': ['Fergana', 'Andijan'],
            'West Region': ['Bukhara', 'Navoi'],
        }
        region_objs = {}
        city_objs = {}
        for rname, cities in regions_cities.items():
            region, _ = Region.objects.update_or_create(
                tenant=tenant, name=rname,
                defaults={'code': rname[:3].upper(), 'is_active': True}
            )
            region_objs[rname] = region
            for cname in cities:
                city, _ = City.objects.update_or_create(
                    tenant=tenant, region=region, name=cname,
                    defaults={'code': cname[:3].upper(), 'is_active': True}
                )
                city_objs[cname] = city
        self.stdout.write(f'  Created {len(region_objs)} regions, {len(city_objs)} cities')

        # ── Products ───────────────────────────────────────────
        products_data = [
            {'code': 'PREM', 'name': 'Premium Insurance Package', 'category': 'Insurance'},
            {'code': 'BASIC', 'name': 'Basic Insurance Package', 'category': 'Insurance'},
            {'code': 'ELITE', 'name': 'Elite Insurance Package', 'category': 'Insurance'},
            {'code': 'FAM', 'name': 'Family Package', 'category': 'Insurance'},
        ]
        product_objs = []
        for pd in products_data:
            prod, _ = Product.objects.update_or_create(
                tenant=tenant, code=pd['code'],
                defaults={'name': pd['name'], 'category': pd['category'], 'is_active': True}
            )
            product_objs.append(prod)
        self.stdout.write(f'  Created {len(product_objs)} products')

        # ── Users & Agents ─────────────────────────────────────
        users_spec = [
            # (username, full_name, email, phone, role, region, city, agent_code, parent_code)
            ('admin', 'Admin User', 'admin@acme.com', '+998900000001', 'ADMIN', 'North Region', 'Tashkent', 'ADM-001', None),
            ('robert', 'Robert Johnson', 'robert@acme.com', '+998900000002', 'MANAGER', 'North Region', 'Tashkent', 'MGR-001', None),
            ('maria', 'Maria Garcia', 'maria@acme.com', '+998909876543', 'SUPERVISOR', 'North Region', 'Tashkent', 'SUP-042', None),
            ('david', 'David Martinez', 'david@acme.com', '+998909876544', 'SUPERVISOR', 'South Region', 'Samarkand', 'SUP-043', None),
            ('lisa', 'Lisa Kim', 'lisa@acme.com', '+998909876545', 'SUPERVISOR', 'West Region', 'Bukhara', 'SUP-044', None),
            ('john', 'John Smith', 'john@acme.com', '+998901234567', 'AGENT', 'North Region', 'Tashkent', 'AG-001', 'SUP-042'),
            ('sarah', 'Sarah Johnson', 'sarah@acme.com', '+998901234568', 'AGENT', 'North Region', 'Chirchik', 'AG-002', 'SUP-042'),
            ('michael', 'Michael Brown', 'michael@acme.com', '+998901234569', 'AGENT', 'South Region', 'Samarkand', 'AG-003', 'SUP-043'),
            ('emily', 'Emily Davis', 'emily@acme.com', '+998901234570', 'AGENT', 'East Region', 'Fergana', 'AG-004', 'SUP-043'),
            ('james', 'James Wilson', 'james@acme.com', '+998901234571', 'AGENT', 'West Region', 'Bukhara', 'AG-005', 'SUP-044'),
            ('anna', 'Anna Lee', 'anna@acme.com', '+998901234572', 'AGENT', 'North Region', 'Tashkent', 'AG-006', 'SUP-042'),
            ('peter', 'Peter Park', 'peter@acme.com', '+998901234573', 'AGENT', 'South Region', 'Karshi', 'AG-007', 'SUP-043'),
            ('lisa_chen', 'Lisa Chen', 'lisa.chen@acme.com', '+998900000010', 'FINANCE', 'North Region', 'Tashkent', 'ACC-001', None),
        ]

        user_objs = {}
        agent_objs = {}

        for spec in users_spec:
            uname, fname, email, phone, role_code, rname, cname, acode, parent_code = spec
            user, created = User.objects.update_or_create(
                username=uname,
                defaults={
                    'full_name': fname,
                    'email': email,
                    'phone_number': phone,
                    'tenant': tenant,
                    'is_active': True,
                    'is_staff': role_code in ('ADMIN', 'MANAGER'),
                    'is_superuser': role_code == 'ADMIN',
                }
            )
            if created:
                user.set_password('Pass1234!')
                user.save()

            UserRole.objects.update_or_create(
                tenant=tenant, user=user, role=roles[role_code]
            )

            region = region_objs[rname]
            city = city_objs[cname]
            agent, _ = Agent.objects.update_or_create(
                tenant=tenant, agent_code=acode,
                defaults={
                    'user': user,
                    'region': region,
                    'city': city,
                    'hired_at': datetime.date(2022, 1, 1) + datetime.timedelta(days=random.randint(0, 700)),
                    'status': 'active',
                }
            )
            user_objs[uname] = user
            agent_objs[acode] = agent

        # Set parent references for agents
        for spec in users_spec:
            uname, fname, email, phone, role_code, rname, cname, acode, parent_code = spec
            if parent_code and parent_code in agent_objs:
                agent = agent_objs[acode]
                agent.parent = agent_objs[parent_code]
                agent.save()

        self.stdout.write(f'  Created {len(user_objs)} users and agents')

        # ── Lead Pipelines & Stages ────────────────────────────
        pipeline_stages = {
            'Premium Insurance': [
                ('Initial Contact', 1, False),
                ('Qualification', 2, False),
                ('Proposal', 3, False),
                ('Negotiation', 4, False),
                ('Closed Won', 5, True),
            ],
            'Basic Insurance': [
                ('Lead', 1, False),
                ('Contact Made', 2, False),
                ('Quote Sent', 3, False),
                ('Closed Won', 4, True),
            ],
            'Elite Insurance': [
                ('Initial Contact', 1, False),
                ('Needs Analysis', 2, False),
                ('Proposal', 3, False),
                ('Negotiation', 4, False),
                ('Final Review', 5, False),
                ('Closed Won', 6, True),
            ],
            'Family Package': [
                ('Lead', 1, False),
                ('Consultation', 2, False),
                ('Quote', 3, False),
                ('Closed Won', 4, True),
            ],
        }

        pipelines = {}
        stages = {}
        for prod in product_objs:
            pname = prod.name.replace(' Package', '')
            if pname in pipeline_stages:
                pipeline, _ = LeadPipeline.objects.update_or_create(
                    tenant=tenant, product=prod, name=f'{prod.name} Pipeline',
                    defaults={'is_active': True}
                )
                pipelines[prod.id] = pipeline
                for sname, sorder, is_terminal in pipeline_stages[pname]:
                    stage, _ = LeadStage.objects.update_or_create(
                        tenant=tenant, pipeline=pipeline, stage_order=sorder,
                        defaults={'name': sname, 'is_terminal': is_terminal, 'is_active': True}
                    )
                    stages[(prod.id, sorder)] = stage

        self.stdout.write(f'  Created {len(pipelines)} pipelines with stages')

        # ── Customers ──────────────────────────────────────────
        first_names = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank', 'Grace',
                       'Henry', 'Iris', 'Jack', 'Karen', 'Leo', 'Mia', 'Noah',
                       'Olivia', 'Paul', 'Quinn', 'Rosa', 'Sam', 'Tina',
                       'Uma', 'Victor', 'Wendy', 'Xavier', 'Yuki', 'Zara',
                       'Ahmad', 'Bekzod', 'Dildora', 'Eldor', 'Feruza', 'Gulnora',
                       'Hamid', 'Ilhom', 'Jasur', 'Kamola', 'Laziz', 'Madina',
                       'Nargiza', 'Otabek', 'Parvina', 'Rustam', 'Sardor', 'Tahir',
                       'Umida', 'Vohid', 'Xurshid', 'Yoqub', 'Zulfiya', 'Amir']
        last_names = ['Cooper', 'Wilson', 'Davis', 'Evans', 'Franklin', 'Green',
                      'Hill', 'Irving', 'Jones', 'King', 'Lewis', 'Moore',
                      'Nelson', 'Owen', 'Perez', 'Quinn', 'Rivera', 'Stone',
                      'Karimov', 'Aliyev', 'Mirzayev', 'Toshmatov', 'Umarov',
                      'Botirov', 'Djuraev', 'Ergashev']

        customer_objs = []
        for i in range(50):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            cust, _ = Customer.objects.get_or_create(
                tenant=tenant,
                phone=f'+99890{random.randint(1000000, 9999999)}',
                defaults={'full_name': f'{fname} {lname}'}
            )
            customer_objs.append(cust)
        self.stdout.write(f'  Created {len(customer_objs)} customers')

        # ── Leads ──────────────────────────────────────────────
        agent_codes = ['AG-001', 'AG-002', 'AG-003', 'AG-004', 'AG-005', 'AG-006', 'AG-007']
        interaction_types = ['Phone', 'Email', 'In Person', 'Online Chat', 'Referral']
        lead_objs = []
        now = timezone.now()

        for i in range(50):
            agent = agent_objs[random.choice(agent_codes)]
            customer = random.choice(customer_objs)
            days_ago = random.randint(0, 90)
            created = now - datetime.timedelta(days=days_ago)

            lead, _ = Lead.objects.get_or_create(
                tenant=tenant,
                agent=agent,
                customer=customer,
                customer_phone=customer.phone,
                defaults={
                    'customer_name': customer.full_name,
                    'interaction_type': random.choice(interaction_types),
                    'server_received_at': created,
                }
            )
            lead_objs.append(lead)

            # Create a lead application for a random product
            prod = random.choice(product_objs)
            if prod.id in pipelines:
                pipeline = pipelines[prod.id]
                max_stage = max(o for (pid, o) in stages.keys() if pid == prod.id)
                stage_order = random.randint(1, max_stage)
                stage = stages.get((prod.id, stage_order))
                if stage:
                    LeadApplication.objects.get_or_create(
                        tenant=tenant,
                        lead=lead,
                        product=prod,
                        pipeline=pipeline,
                        defaults={
                            'current_stage': stage,
                            'is_primary': True,
                            'status_last_updated_at': created,
                        }
                    )

        self.stdout.write(f'  Created {len(lead_objs)} leads')

        # ── Sales ──────────────────────────────────────────────
        sale_objs = []
        for i in range(30):
            agent = agent_objs[random.choice(agent_codes)]
            customer = random.choice(customer_objs)
            prod = random.choice(product_objs)
            days_ago = random.randint(0, 90)
            sold_at = now - datetime.timedelta(days=days_ago)
            amount = Decimal(str(random.randint(800, 5000)))

            # Find a matching lead if any
            lead = Lead.objects.filter(agent=agent, customer=customer, tenant=tenant).first()

            sale, created = Sale.objects.get_or_create(
                tenant=tenant,
                agent=agent,
                customer=customer,
                product=prod,
                sold_at=sold_at,
                defaults={
                    'lead': lead,
                    'amount': amount,
                    'status': 'completed',
                }
            )
            if created:
                sale_objs.append(sale)

        self.stdout.write(f'  Created {len(sale_objs)} sales')

        # ── Bonus Rules ────────────────────────────────────────
        bonus_rules = [
            {
                'name': 'High Value Sale Bonus',
                'rule_dimension': 'SELL_AMOUNT',
                'operator': 'GTE',
                'num_from': Decimal('5000'),
                'amount_type': 'percent_of_sale',
                'amount_value': Decimal('15.0000'),
                'cap_amount': Decimal('1000'),
                'is_active': True,
                'effective_from': timezone.now() - datetime.timedelta(days=365),
            },
            {
                'name': 'Quick Conversion Bonus',
                'rule_dimension': 'LEAD_TO_SELL_DELTA',
                'operator': 'LTE',
                'interval_from': datetime.timedelta(days=2),
                'amount_type': 'fixed',
                'amount_value': Decimal('100.0000'),
                'is_active': True,
                'effective_from': timezone.now() - datetime.timedelta(days=365),
            },
            {
                'name': 'Premium Product Bonus',
                'rule_dimension': 'POTENTIAL_PRODUCT',
                'operator': 'IN',
                'text_values': 'Premium, Elite',
                'amount_type': 'percent_of_sale',
                'amount_value': Decimal('12.0000'),
                'cap_amount': Decimal('800'),
                'is_active': True,
                'effective_from': timezone.now() - datetime.timedelta(days=365),
            },
            {
                'name': 'Weekend Sale Bonus',
                'rule_dimension': 'SELL_TIME',
                'operator': 'BETWEEN',
                'text_value': 'Sat-Sun',
                'amount_type': 'fixed',
                'amount_value': Decimal('50.0000'),
                'is_active': False,
                'effective_from': timezone.now() - datetime.timedelta(days=365),
            },
        ]
        for br in bonus_rules:
            BonusRule.objects.update_or_create(
                tenant=tenant, name=br.pop('name'),
                defaults=br
            )
        self.stdout.write(f'  Created {len(bonus_rules)} bonus rules')

        # ── Commission Policy ──────────────────────────────────
        CommissionPolicy.objects.update_or_create(
            tenant=tenant, name='Default Attribution Policy',
            defaults={
                'mode': 'LAST_TOUCH',
                'window_interval': datetime.timedelta(days=30),
                'effective_from': timezone.now() - datetime.timedelta(days=365),
                'is_active': True,
            }
        )
        self.stdout.write('  Created commission policy')

        # ── KPI Agent Daily (last 90 days) ─────────────────────
        kpi_count = 0
        today = timezone.now().date()
        agent_list = [agent_objs[c] for c in agent_codes]

        for agent in agent_list:
            for day_offset in range(90):
                kpi_date = today - datetime.timedelta(days=day_offset)
                # Skip weekends sometimes
                if kpi_date.weekday() >= 5 and random.random() < 0.3:
                    continue

                leads_captured = random.randint(2, 12)
                leads_converted = random.randint(0, min(leads_captured, 5))
                conv_rate = Decimal(str(round(leads_converted / max(leads_captured, 1) * 100, 2)))
                revenue = Decimal(str(leads_converted * random.randint(800, 2500)))
                bonus = Decimal(str(round(float(revenue) * random.uniform(0.05, 0.15), 2)))
                net_profit = revenue - bonus

                KPIAgentDaily.objects.update_or_create(
                    tenant=tenant,
                    agent=agent,
                    kpi_date=kpi_date,
                    defaults={
                        'leads_captured': leads_captured,
                        'leads_converted': leads_converted,
                        'conversion_rate': conv_rate,
                        'revenue_amount': revenue,
                        'bonus_amount': bonus,
                        'net_profit': net_profit,
                        'avg_time_to_convert': datetime.timedelta(hours=random.randint(2, 72)),
                    }
                )
                kpi_count += 1

        self.stdout.write(f'  Created {kpi_count} KPI daily records')

        self.stdout.write(self.style.SUCCESS(
            '\nSeed data created successfully!\n'
            'Login credentials (all passwords: Pass1234!):\n'
            '  admin    / Pass1234!  (Admin)\n'
            '  robert   / Pass1234!  (Manager)\n'
            '  maria    / Pass1234!  (Supervisor)\n'
            '  john     / Pass1234!  (Agent)\n'
            '  lisa_chen / Pass1234!  (Accountant)\n'
        ))
