from rest_framework import serializers
from .models import Meeting, Section, MeetingParticipant
from organizations.models import Organization

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'title', 'start_time', 'end_time', 'total_duration', 'is_active', 'is_paused', 'organization']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name', 'duration', 'start_time', 'end_time', 'meeting']

class MeetingCreateSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, required=False)

    class Meta:
        model = Meeting
        fields = ['title', 'start_time', 'end_time', 'total_duration', 'organization', 'sections']

    def create(self, validated_data):
        sections_data = validated_data.pop('sections', [])
        meeting = Meeting.objects.create(**validated_data)

        for section_data in sections_data:
            Section.objects.create(meeting=meeting, **section_data)

        return meeting
