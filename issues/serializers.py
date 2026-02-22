from rest_framework import serializers
from issues.models import Complaint, LostItemTicket, TicketStatusLookup, SLAPolicy, SLAIssueType


CATEGORY_TO_SLA_ISSUE_TYPE = {
    'SAFETY': 'SOS',
    'BILLING': 'COMPLAINT',
    'OTHER': 'COMPLAINT',
}


# Serializer for Complaint
class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            'complaint_id',
            'user',
            'ride',
            'description',
            'category',
            'complaint_status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'complaint_id',
            'complaint_status',
            'created_at',
            'updated_at'
        ]

    def validate(self, data):
        if not data.get('description'):
            raise serializers.ValidationError({'description': 'Description is required.'})

        if not data.get('category'):
            raise serializers.ValidationError({'category': 'Category is required.'})

        return data

    def create(self, validated_data):
        category_obj = validated_data['category']
        category_name = category_obj.category  # SAFETY / BILLING / OTHER

        # 🔹 Resolve SLA Issue Type
        try:
            sla_issue_type = SLAIssueType.objects.get(
                sla_issue_type='COMPLAINT'
            )
        except KeyError:
            raise serializers.ValidationError({
                'category': 'No SLA mapping defined for this category.'
            })
        except SLAIssueType.DoesNotExist:
            raise serializers.ValidationError({
                'category': 'SLA issue type not found for this category.'
            })

        # 🔹 Resolve SLA Policy (assuming one active per issue type)
        try:
            sla_policy = SLAPolicy.objects.get(
                sla_issue_type=sla_issue_type,
                priority = 4,
            )

            # for sla_polic in sla_policy:
        except SLAPolicy.DoesNotExist:
            raise serializers.ValidationError({
                'category': 'No active SLA policy configured for this category.'
            })

        # 🔹 Default ticket status
        open_status = TicketStatusLookup.objects.get(ticket_status='OPEN')

        validated_data['sla_policy'] = sla_policy
        validated_data['complaint_status'] = open_status

        return super().create(validated_data)


class ComplaintListSerializer(serializers.ModelSerializer):
    complaint_status_display = serializers.CharField(
        source='complaint_status.ticket_status',
        read_only=True
    )

    class Meta:
        model = Complaint
        fields = [
            'complaint_id',
            'ride',
            'description',
            'category',
            'complaint_status',
            'complaint_status_display',
            'created_at',
            'updated_at'
        ]


# Serializer for LostItemTicket
class LostItemTicketSerializer(serializers.ModelSerializer):
    ticket_status_display = serializers.CharField(
        source='ticket_status.ticket_status',
        read_only=True
    )
    class Meta:
        model = LostItemTicket
        fields = ['ticket_id', 'ride', 'ticket_status', 'ticket_status_display', 'raised_by', 'concerned_user', 'concerned_driver', 'created_at', 'closed_at', 'description']

        read_only_fields = [
            'ticket_id',
            'concerned_driver',
            'created_at',
            'closed_at'
        ]
    
    def validate(self, data):
        if not data.get('description'):
            raise serializers.ValidationError('Description is required.')
        return data
    
    def create(self, validated_data):
        ride = validated_data['ride']

        # 🔹 Fetch driver from Ride
        driver = ride.driver  # FK access, no extra query

        if not driver:
            raise serializers.ValidationError({
                'ride': 'No driver associated with this ride.'
            })

        validated_data['concerned_driver'] = driver

        return super().create(validated_data)


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            'description',
            'complaint_status',
            'category'
        ]

    def validate(self, data):
        if not data:
            raise serializers.ValidationError('No data provided for update.')
        return data


class LostItemTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LostItemTicket
        fields = [
            'ticket_status',
            'description',
            'closed_at'
        ]

    def validate(self, data):
        if not data:
            raise serializers.ValidationError('No data provided for update.')
        return data
