from collections import deque
from rest_framework.exceptions import NotFound, ValidationError


class BulkEditAPIMixin(object):
    details_serializer_class = None
    # how many items can be edited at once, disabled if None
    BULK_EDIT_MAX_ITEMS = None
    BULK_EDIT_ALLOW_DELETE_ITEMS = False

    def _get_item_id_key(self, item):
        """Items use id for update and delete and temp_id for create"""
        for key in ["id", "temp_id"]:
            if key in item:
                return key

        return None

    def _get_bulk_edit_items(self, data):
        """Filter out items and put them for update, create or delete"""
        items = {"create": {}, "update": {}, "delete": {}}
        for request_item in data:
            # to create, FE must pass "temp_id" so they will be able to match the response
            # in case of any validation errors
            id_key = self._get_item_id_key(request_item)
            item_id = request_item.get(id_key)
            if not isinstance(item_id, int):
                continue

            if self.BULK_EDIT_ALLOW_DELETE_ITEMS and request_item.get("delete_object"):
                change_type = "delete"
            elif id_key == "id":
                change_type = "update"
            elif hasattr(self, "create") and id_key == "temp_id":
                change_type = "create"

            items[change_type][item_id] = request_item

        return items

    def _perform_bulk_edit(self, items):
        update_delete_ids = set(items["update"].keys()) | set(items["delete"].keys())
        update_delete_objects = {item.id: item for item in self.get_queryset().filter(id__in=update_delete_ids)}
        update_delete_objects_ids = set(update_delete_objects.keys())
        if update_delete_ids != update_delete_objects_ids:
            not_found_ids = update_delete_ids - update_delete_objects_ids
            raise NotFound(
                [{"id": item_id, "non_field_errors": ["This item does not exist."]} for item_id in not_found_ids]
            )

        errors = []
        actions = deque()
        for change_type in items:
            for item_id, item in items[change_type].items():
                if change_type == "create":
                    instance = None
                    serializer = self.get_serializer(data=item)
                    action = serializer.save
                elif change_type in ["update", "delete"]:
                    instance = update_delete_objects[item_id]
                    serializer = self.get_details_serializer(instance=instance, data=item, partial=True)
                    action = {"update": serializer.save, "delete": instance.delete}[change_type]

                id_key = self._get_item_id_key(item)
                if serializer and not serializer.is_valid():
                    item_error = {id_key: item_id}
                    item_error.update(serializer.errors)
                    errors.append(item_error)
                    continue

                # success - change can be made
                actions.append(action)

        if errors:
            raise ValidationError(errors)

        # perform actions if valdiation passed
        for action in actions:
            action()

    def get_details_serializer_class(self):
        assert self.details_serializer_class is not None, (
            f"{self.__class__.__name__} should either include a `details_serializer_class` attribute, "
            "or override the `get_details_serializer_class()` method."
        )
        return self.details_serializer_class

    def get_details_serializer(self, *args, **kwargs):
        """Get instance of details serializer for bulk edit"""
        serializer_class = self.get_details_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Bulk edit for member medications"""
        if not isinstance(request.data, list):
            raise ValidationError({"non_field_errors": ["Payload for bulk edit must be a list of objects to edit."]})

        if self.BULK_EDIT_MAX_ITEMS and len(request.data) > self.BULK_EDIT_MAX_ITEMS:
            raise ValidationError(
                {"non_field_errors": [f"Cannot edit more than {self.BULK_EDIT_MAX_ITEMS} items at once."]}
            )

        items = self._get_bulk_edit_items(request.data)
        self._perform_bulk_edit(items)
        return self.list(request, *args, **kwargs)
