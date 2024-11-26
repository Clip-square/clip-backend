from rest_framework import serializers
from .models import Meeting, Section, MeetingParticipant
from accounts.models import CustomUser
from accounts.serializers import UserSerializer

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['name']
    
class MeetingParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = MeetingParticipant
        fields = ['user']
        
class MeetingCreateSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, required=False)
    user_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    participants = MeetingParticipantSerializer(source='meetingparticipant_set', many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = ['title', 'total_duration', 'organization', 'sections', 'user_ids', 'save_minutes', 'participants']

    def create(self, validated_data):
        sections_data = validated_data.pop('sections', [])
        user_ids = validated_data.pop('user_ids', [])
        meeting = Meeting.objects.create(**validated_data)

        for section_data in sections_data:
            Section.objects.create(meeting=meeting, **section_data)

        for user_id in user_ids:
            try:
                user = CustomUser.objects.get(id=user_id)
                MeetingParticipant.objects.create(meeting=meeting, user=user)
            except CustomUser.DoesNotExist:
                continue 

        return meeting