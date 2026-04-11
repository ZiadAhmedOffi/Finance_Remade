from django.db import transaction, IntegrityError

def locked_get_or_create(model, defaults=None, **kwargs):
    with transaction.atomic():
        try:
            obj = model.objects.select_for_update().get(**kwargs)
            return obj, False
        except model.DoesNotExist:
            try:
                params = {**kwargs, **(defaults or {})}
                obj = model.objects.create(**params)
                return obj, True
            except IntegrityError:
                obj = model.objects.get(**kwargs)
                return obj, False