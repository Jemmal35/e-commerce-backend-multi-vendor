from rest_framework import serializers
from apps.vendors.models import Vendor
from apps.vendors.models import VENDOR_STATUS

from apps.core.models import ActivityLog


class AdminVendorUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VENDOR_STATUS.choices)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Vendor
        fields = ['status', 'rejection_reason']

    def validate(self, attrs):
        status = attrs.get('status')
        rejection_reason = attrs.get('rejection_reason')

        if status == VENDOR_STATUS.REJECTED and not rejection_reason:
            raise serializers.ValidationError("Rejection reason is required when rejecting a vendor application.")
        
        # if status != VENDOR_STATUS.REJECTED and rejection_reason:
        #     raise serializers.ValidationError("Rejection reason should only be provided when rejecting a vendor application.")

        return attrs
    


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'actor', 'actor_email', 'method', 'path', 'status_code', 'ip_address', 'request_payload', 'timestamp']