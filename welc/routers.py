class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'welc':
            if model._meta.model_name in ['confirmation', 'tag', 'cashentry', 'member']:
                return 'pamco'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'welc':
            if model._meta.model_name in ['taggeneration', 'transactionlog']:
                return 'default'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        db_set = {'default', 'pamco'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'welc':
            if model_name in ['taggeneration', 'transactionlog', 'garmentproduct']:
                return db == 'default'
            if model_name in ['confirmation', 'tag', 'cashentry', 'member']:
                return db == 'pamco'
        return db == 'default'