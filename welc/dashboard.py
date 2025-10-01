# welc/dashboard.py
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, AppIndexDashboard
from django.urls import reverse

class CustomIndexDashboard(Dashboard):
    columns = 3

    def init_with_context(self, context):
        # User Management Section
        self.children.append(modules.ModelList(
            title='User Profiles',
            models=('myapp.models.Profile',),
            column=0,
            order=0
        ))

        # Production Tracking
        self.children.append(modules.ModelList(
            title='Production Tracking',
            models=(
                'welc.models.TagGeneration',
                'welc.models.GarmentProduct',
                'welc.models.TransactionLog',
            ),
            column=0,
            order=1
        ))

        # Recent Actions
        self.children.append(modules.RecentActions(
            title='Recent Activities',
            include_list=('welc.*', 'myapp.*'),
            limit=10,
            column=1,
            order=0
        ))

        # Quick Actions
        self.children.append(modules.LinkList(
            title='Quick Actions',
            layout='inline',
            children=[
                {
                    'title': 'Create New Tag',
                    'url': '/admin/welc/taggeneration/add/',
                    'external': False,
                },
                {
                    'title': 'Register Tannery',
                    'url': '/admin/welc/tannery/add/',
                    'external': False,
                },
                {
                    'title': 'View Garments',
                    'url': '/admin/welc/garmentproduct/',
                    'external': False,
                },
            ],
            column=2,
            order=0
        ))


        # Status Overview
        self.children.append(modules.RecentActions(
            title='System Status',
            limit=5,
            column=1,
            order=1
        ))