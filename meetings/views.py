from django.http import JsonResponse
import asyncio
from asgiref.sync import sync_to_async
from sentence_transformers import SentenceTransformer, util
import base64
from pydub import AudioSegment
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Meeting
from .serializers import MeetingCreateSerializer
from accounts.authenticate import SafeJWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from organizations.models import Organization
from datetime import datetime
from background_task import background
from datetime import timedelta
import os
from tqdm import tqdm
import numpy as np
import soundfile as sf
import librosa
import glob
import speech_recognition as sr
import nemo.collections.asr as nemo_asr
from simple_diarizer.diarizer import Diarizer
import openai
import json


class MeetingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="회의 생성",
        operation_description="새로운 회의를 생성합니다.",
        request_body=MeetingCreateSerializer,
        responses={
            201: openapi.Response(
                description='Meeting created successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
                        'meeting': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                                'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                                'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                                'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                                'sections': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                        }
                                    ),
                                    description='회의의 섹션 리스트'
                                ),
                                'participants': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'user': openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                                    'name': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                                    'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                                },
                                                description='참여자 정보'
                                            )
                                        }
                                    ),
                                    description='참여자 리스트'
                                ),
                                'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description='Bad Request'),
            401: openapi.Response(description='Authentication failed')
        }
    )
    def post(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = MeetingCreateSerializer(data=request.data)
        if serializer.is_valid():
            meeting = serializer.save(creator=user)
            return Response({"message": "Meeting created successfully", "meeting": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="회의 전체 조회",
        operation_description="사용자가 참가 중인 조직 내의 모든 회의 정보를 조회합니다.",
        responses={
            200: openapi.Response(
                description='Meetings retrieved successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'meetings': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                                    'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                                    'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                                    'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                                    'sections': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                                'end_time': openapi.Schema(type=openapi.TYPE_INTEGER, description='섹션 종료 시간 (분 단위)'),

                                            }
                                        )
                                    ),
                                    'participants': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'user': openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                                    }
                                                )
                                            }
                                        )
                                    ),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                                    'is_active': openapi.Schema(
                                        type=openapi.TYPE_STRING, 
                                        description='활성 상태 ("true", "ongoing", "false")',
                                        enum=["true", "ongoing", "false"], 
                                    ),    
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description='Authentication failed'),
        }
    )
    def get(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_organizations = Organization.objects.filter(members__user=user)
    
        if not user_organizations.exists():
            return Response({'meetings': []}, status=status.HTTP_200_OK)

        meetings = Meeting.objects.filter(organization__in=user_organizations)
        serializer = MeetingCreateSerializer(meetings, many=True)
        return Response({"meetings": serializer.data}, status=status.HTTP_200_OK)


class MeetingDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="단일 회의 조회",
        operation_description="특정 ID를 가진 단일 회의 정보를 조회합니다.",
        responses={
            200: openapi.Response(
                description='Meeting retrieved successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                        'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                        'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                        'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                        'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                        'sections': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                    'end_time': openapi.Schema(type=openapi.TYPE_INTEGER, description='섹션 종료 시간 (분 단위)'),
                                }
                            )
                        ),
                        'participants': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'user': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                        }
                                    )
                                }
                            )
                        ),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                        'is_active': openapi.Schema(
                            type=openapi.TYPE_STRING, 
                            description='활성 상태 ("true", "ongoing", "false")',
                            enum=["true", "ongoing", "false"], 
                        ),
                    }
                )
            ),
            401: openapi.Response(description='Authentication failed'),
            404: openapi.Response(description='Meeting not found')
        }
    )
    def get(self, request, meeting_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MeetingCreateSerializer(meeting)
        return Response(serializer.data, status=status.HTTP_200_OK)


openai.api_key = os.getenv("OPENAI_API_KEY")

model = SentenceTransformer('all-MiniLM-L6-v2')


if os.path.exists("meetings/minutes_vector_db.npz"):
    minutes_vector_db = np.load("meetings/minutes_vector_db.npz", encoding='latin1', allow_pickle=True)

    summary_vector_db = np.load("meetings/summary_vector_db.npz", encoding='latin1', allow_pickle=True)

    print("File loaded successfully")
else:
    print("File not found at path:", "meetings/minutes_vector_db.npz")


class MeetingStatusUpdateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="회의 상태를 'ongoing'으로 업데이트",
        operation_description="회의 상태를 'ongoing'으로 변경합니다.",
        responses={
            200: openapi.Response(description='회의 상태가 성공적으로 업데이트되었습니다.'),
            400: openapi.Response(description='요청이 올바르지 않습니다.'),
            401: openapi.Response(description='인증 실패'),
            404: openapi.Response(description='회의를 찾을 수 없습니다.')
        }
    )
    def post(self, request, meeting_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "회의를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        meeting.is_active = "ongoing"
        meeting.save()

        return Response({"message": "회의 상태가 'ongoing'으로 성공적으로 업데이트되었습니다."}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="회의 상태를 'false'로 업데이트",
        operation_description="회의 상태를 'false'로 변경하며 회의 종료 데이터를 처리합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'record_file': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="binary",
                    description="업로드할 녹음 파일 (wav 형식)"
                ),
                'total_duration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="duration",
                    description="총 회의 시간 (예: '01:30:00')"
                ),
                'section_end_times': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING, format="date-time"),
                    description="각 섹션 종료 시간"
                ),
                'start_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="date",
                    description="회의 시작 날짜"
                ),
            },
            required=['record_file', 'total_duration', 'section_end_times', 'start_time'],
        ),
        responses={
            200: openapi.Response(description="회의 상태가 성공적으로 업데이트되었습니다."),
            400: openapi.Response(description="요청이 올바르지 않습니다."),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="회의를 찾을 수 없습니다.")
        }
    )
    def delete(self, request, meeting_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "회의를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 요청 데이터 검증
        data = request.data
        record_file = request.FILES.get('record_file') 
        total_duration = data.get('total_duration')
        section_end_times = data.getlist('section_end_times[]')
        start_time = data.get('start_time')
        end_time = datetime.now() 
        
        meeting = Meeting.objects.get(id=meeting_id)
        num_speakers = meeting.attendees.count()  

        
        if not record_file or not total_duration or not section_end_times or not start_time:
            return Response({"error": "요청 데이터가 누락되었습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not record_file.name.endswith('.wav'):
            return Response({"error": "녹음 파일은 .wav 형식이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        record_file_data = record_file.read()
        record_file_base64 = base64.b64encode(record_file_data).decode('utf-8')

        meeting.is_active = "false"
        meeting.end_time = end_time
        meeting.total_duration = total_duration
        meeting.start_time = start_time
        meeting.save()
        
        section_titles = list(meeting.sections.values_list('name', flat=True))

        process_meeting_data(
            meeting_id=meeting.id,
            meeting_title=meeting.title,
            section_titles=section_titles,
            record_file_data=record_file_base64,
            start_time=start_time,
            section_end_times=section_end_times,
            num_speakers=num_speakers,
            schedule=0
        )

        sections = meeting.sections.all()
        
        if len(sections) != len(section_end_times):
            return Response({"error": "섹션 개수와 종료 시간 개수가 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        for section, section_end_time in zip(sections, section_end_times):
            section.end_time = section_end_time
            section.save()

        return Response({"message": "회의 상태가 'false'로 성공적으로 업데이트되었습니다."}, status=status.HTTP_200_OK)


@background(schedule=0)
def process_meeting_data(meeting_id, meeting_title, section_titles, section_end_times, start_time, record_file_data, num_speakers):
    try:
        record_file_data_bytes = base64.b64decode(record_file_data)
        file_content = BytesIO(record_file_data_bytes)

        meeting = Meeting.objects.get(id=meeting_id)

        base_dir = os.getcwd() 
        save_dir = os.path.join(base_dir, f"meetings", f"meeting_{meeting.id}")
        voice_seg_dir = os.path.join(base_dir, f"meetings", f"meeting_{meeting.id}", f"segmented")
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        start_time = convert_to_timedelta(start_time)

        section_end_times = [convert_to_timedelta(time) for time in section_end_times]

        audio, sr_ = librosa.load(file_content, sr=16000, mono=False)
        
        if audio.ndim == 1:
            audio = audio[:, None]
            audio = audio.repeat(2, axis=1)
        
        print(f"Audio loaded: {audio.shape} samples at {sr_} Hz")

        section_start = start_time
        section_file_paths = [] 
        for idx, section_end in enumerate(section_end_times):
            start_sample = int(section_start.total_seconds() * sr_) 
            end_sample = int(section_end.total_seconds() * sr_) 

            section_audio = audio[start_sample:end_sample, :] 
            section_filename = f"section_{idx + 1}.wav"
            section_audio_path = os.path.join(save_dir, section_filename)

            print(f"Saving section {idx + 1} to {section_audio_path}")
            sf.write(section_audio_path, section_audio, sr_)
            section_file_paths.append(section_audio_path)

            section_start = section_end

            print(f"Section {idx + 1} ({meeting_title}) 저장 완료: {section_filename}")

        model_name = "eesungkim/stt_kr_conformer_transducer_large" 
        asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name)
        
        file_names = [i for i in os.listdir(save_dir) if 'wav' in i]
        
        all_stt_results = []
        
        for file_name in tqdm(file_names):
            print(f"Processing {file_name}...")
            
            diar = Diarizer(embed_model='xvec', cluster_method='sc')

            # 파일 경로 설정
            file_path = os.path.join(save_dir, file_name)

            # 소리 파일 읽기
            sound_raw, sr_ = sf.read(file_path)
            
            seg_initial = diar.diarize(file_path)
            
            detected_speakers = len(set([seg_['label'] for seg_ in seg_initial]))
            num_speakers = min(num_speakers, detected_speakers)

            seg = diar.diarize(file_path, num_speakers=num_speakers)
            
            # 음성 파일 분할 폴더 준비
            if os.path.exists(voice_seg_dir):
                files = glob.glob(f'{voice_seg_dir}/*')
                for f in files:
                    os.remove(f)
            else:
                os.makedirs(voice_seg_dir)

            # 화자 분리된 오디오 저장
            for diar_num, seg_ in enumerate(seg):
                start_index = seg_['start_sample']
                end_index = seg_['end_sample'] + 1
                speaker = seg_['label']
                diar_num_str = str(diar_num).zfill(3)
                slice_voice_path = f"{voice_seg_dir}/diar{diar_num_str}_speaker{speaker}.wav"
                sf.write(slice_voice_path, sound_raw[start_index:end_index], sr_)

            # 분할된 파일 순회하며 STT 처리
            seg_file_list = np.sort(os.listdir(voice_seg_dir))
            stt_dict = {i: [] for i in range(num_speakers)} 

            for file_name_ in seg_file_list:
                try:
                    file_path_ = os.path.join(voice_seg_dir, file_name_)
                    r = sr.Recognizer()

                    with sr.AudioFile(file_path_) as source:
                        audio = r.record(source)

                    # 구글 음성 인식 서비스로 STT 실행
                    stt = r.recognize_google(audio, language='ko-KR', show_all=True)
                    diar_info = file_name_.replace('.wav', '')

                    # STT 결과를 화자별로 저장
                    if 'alternative' in stt and len(stt['alternative']) > 0:
                        transcripts = [alt['transcript'] for alt in stt['alternative']]
                        stt_text = ' '.join(transcripts)  # 결과 텍스트 합치기
                        speaker = file_name_.split('_')[-1][7]  # speaker 번호 추출
                        stt_dict[int(speaker)].append(stt_text)  # 화자별로 텍스트 저장

                except sr.UnknownValueError:
                    print(f"Google Speech Recognition could not understand audio in {file_name_}.")
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service for {file_name_}; {e}")
                except Exception as e:
                    print(f"Error processing {file_name_}: {e}")

            # 현재 파일에 대한 STT 결과를 합친 텍스트로 저장
            file_stt_results = []
            for speaker, transcripts in stt_dict.items():
                result = f"speaker{speaker}: {' '.join(transcripts)},"  # 화자별 텍스트 합치기
                file_stt_results.append(result)
            
            # 현재 파일에 대한 결과를 전체 결과 리스트에 추가
            all_stt_results.append(' '.join(file_stt_results))  # 화자별 결과 합친 텍스트

        # 최종 STT 결과 배열 확인
        print(all_stt_results)
        
        asyncio.run(save_minutes(meeting=meeting, topic=meeting_title, sub_topic_list=section_titles, speech_list=all_stt_results, date=start_time))

    except Meeting.DoesNotExist:
        print(f"회의 ID {meeting_id}를 찾을 수 없습니다.")
    except Exception as e:
        print(f"비동기 작업 처리 중 오류 발생: {e}")
        
async def save_minutes(meeting, topic, sub_topic_list, speech_list, date):
    minutes = await create_minutes(topic, sub_topic_list, speech_list, date)
    await save_meeting_minutes(meeting, minutes)

def convert_to_timedelta(time_str):
    """
    시간 형식을 'YYYY-MM-DD HH:MM:SS' 또는 'HH:MM:SS'에서 timedelta로 변환하는 함수.
    """
    try:
        time_str = time_str.strip()
        
        # 날짜만 있는 경우 (예: '2024-12-01')
        if '-' in time_str and len(time_str.split('-')[2]) == 2:  # 'YYYY-MM-DD' 형식
            # 날짜만 있으므로, 시간을 00:00:00으로 설정
            time_obj = datetime.strptime(time_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            return timedelta(hours=time_obj.hour, minutes=time_obj.minute, seconds=time_obj.second)
        
        # 날짜가 포함된 경우(예: '2024-12-01 00:00:00') 처리
        elif ' ' in time_str:
            # '2024-12-01 00:00:00' 형식
            time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return timedelta(hours=time_obj.hour, minutes=time_obj.minute, seconds=time_obj.second)
        
    except Exception as e:
        print(f"시간 변환 오류: {e}", time_str)
        return timedelta(0)  # 오류가 발생하면 기본값으로 0초 반환
    
def retrieve_summary_style(text, vector_db):
    embeddings = vector_db['data']
    metadata = vector_db['indices']

    # 입력 텍스트의 벡터 추출
    text_embedding = model.encode(text)  # (1, 384)
    
    # embeddings가 2D 배열인지 확인 후 (N, 384) 형태로 처리
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(-1, 384)  # (N, 384)로 변환
    
    # 데이터 타입을 맞추기 (float32로 변환)
    text_embedding = text_embedding.astype(np.float32)
    embeddings = embeddings.astype(np.float32)
    
    # 유사도 계산
    similarity = util.cos_sim(text_embedding, embeddings)  # (1, N) 형태의 결과
    
    # 가장 높은 유사도를 가진 인덱스 찾기
    best_match_idx = similarity.argmax()
    
    # 관련된 요약 스타일 반환
    return metadata[best_match_idx]


# 벡터 DB에서 회의 주제 검색
def retrieve_minutes_topic(text, vector_db):
    embeddings = vector_db['data']
    metadata = vector_db['indices']

    # 입력 텍스트의 벡터 추출
    text_embedding = model.encode(text)  # (1, 384)
    
    # embeddings가 2D 배열인지 확인 후 (N, 384) 형태로 처리
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(-1, 384)  # (N, 384)로 변환
    
    similarity = util.cos_sim(text_embedding, embeddings)
    best_match_idx = similarity.argmax()
    return metadata[best_match_idx]

# GPT-4 API 호출
async def generate_summary(prompt):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 전문 회의록 작성자입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# 회의록 생성
async def create_minutes(topic, sub_topic_list, speech_list, date):
    summaries = []
    for sub_topic, speech in zip(sub_topic_list, speech_list):
        summary_style = retrieve_summary_style(speech, summary_vector_db)
        prompt = f"""
        다음 스타일로 회의 내용을 요약하세요:
        {summary_style}

        소주제: {sub_topic}
        내용: {speech}
        """
        summary = await generate_summary(prompt)
        summaries.append(f"## {sub_topic}\n{summary}")

    minutes_topic_info = retrieve_minutes_topic(topic, minutes_vector_db)
    minutes_topic_info_text = "\n".join(minutes_topic_info) if isinstance(minutes_topic_info, list) else minutes_topic_info

    minutes = f"# {topic}\n\n**회의 일시**: {date}\n\n" + "\n\n".join(summaries) + f"\n\n---\n\n### 종합 정리\n{minutes_topic_info_text}"
    return minutes

@sync_to_async
def save_meeting_minutes(meeting, minutes):
    meeting.meeting_minutes = minutes
    meeting.save()