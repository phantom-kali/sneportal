from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from exam.models import Subject, Exam, Question
from django.db import transaction

class Command(BaseCommand):
    help = 'Populate the database with sample subjects, exams, and questions'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                # Create or get admin user
                admin_user, created = User.objects.get_or_create(
                    username='admin',
                    defaults={
                        'is_staff': True,
                        'is_superuser': True
                    }
                )
                if created:
                    admin_user.set_password('admin123')
                    admin_user.save()
                    self.stdout.write(self.style.SUCCESS('Created admin user'))

                # Create subjects
                subjects_data = [
                    {'name': 'Mathematics', 'code': 'MATH'},
                    {'name': 'English', 'code': 'ENG'},
                    {'name': 'Kiswahili', 'code': 'SWA'},
                    {'name': 'Science', 'code': 'SCI'}
                ]

                subjects = {}
                for subject_data in subjects_data:
                    subject, created = Subject.objects.get_or_create(**subject_data)
                    subjects[subject_data['code']] = subject
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created subject: {subject.name}'))

                # Create exams with questions
                exams_data = {
                    'MATH': {
                        'title': 'Grade 3 Mathematics Assessment',
                        'grade_level': 'Grade 3',
                        'duration_minutes': 30,
                        'language': 'en',
                        'instructions': 'Listen carefully to each question and provide your answer.',
                        'questions': [
                            {
                                'text': 'What is 5 plus 7?',
                                'type': 'multiple_choice',
                                'options': {'A': '10', 'B': '12', 'C': '13', 'D': '15'},
                                'correct': 'B',
                                'points': 2
                            },
                            {
                                'text': 'Is 20 greater than 15?',
                                'type': 'true_false',
                                'correct': 'true',
                                'points': 1
                            },
                            {
                                'text': 'What is 4 times 3?',
                                'type': 'short_answer',
                                'correct': '12',
                                'points': 2
                            }
                        ]
                    },
                    'ENG': {
                        'title': 'Grade 3 English Comprehension',
                        'grade_level': 'Grade 3',
                        'duration_minutes': 25,
                        'language': 'en',
                        'instructions': 'Listen to each question carefully and answer in clear English.',
                        'questions': [
                            {
                                'text': 'Which word means the opposite of "happy"?',
                                'type': 'multiple_choice',
                                'options': {'A': 'sad', 'B': 'glad', 'C': 'mad', 'D': 'bad'},
                                'correct': 'A',
                                'points': 1
                            },
                            {
                                'text': 'Is a cat bigger than an elephant?',
                                'type': 'true_false',
                                'correct': 'false',
                                'points': 1
                            },
                            {
                                'text': 'What is the color of the sky on a clear day?',
                                'type': 'short_answer',
                                'correct': 'blue',
                                'points': 2
                            }
                        ]
                    },
                    'SWA': {
                        'title': 'Mtihani wa Kiswahili Darasa la Tatu',
                        'grade_level': 'Darasa 3',
                        'duration_minutes': 25,
                        'language': 'sw',
                        'instructions': 'Sikiliza kwa makini kila swali na utoe jibu lako.',
                        'questions': [
                            {
                                'text': 'Neno lipi lina maana sawa na "furaha"?',
                                'type': 'multiple_choice',
                                'options': {'A': 'raha', 'B': 'huzuni', 'C': 'wasiwasi', 'D': 'hasira'},
                                'correct': 'A',
                                'points': 1
                            },
                            {
                                'text': 'Ndege wote wanaweza kuruka?',
                                'type': 'true_false',
                                'correct': 'false',
                                'points': 1
                            },
                            {
                                'text': 'Mnyama anayeishi majini na nchi kavu anaitwa nini?',
                                'type': 'short_answer',
                                'correct': 'chura',
                                'points': 2
                            }
                        ]
                    },
                    'SCI': {
                        'title': 'Grade 3 Science Assessment',
                        'grade_level': 'Grade 3',
                        'duration_minutes': 30,
                        'language': 'en',
                        'instructions': 'Listen to each question and provide your best answer.',
                        'questions': [
                            {
                                'text': 'Which animal lays eggs?',
                                'type': 'multiple_choice',
                                'options': {'A': 'cat', 'B': 'dog', 'C': 'chicken', 'D': 'cow'},
                                'correct': 'C',
                                'points': 1
                            },
                            {
                                'text': 'Do all plants need water to grow?',
                                'type': 'true_false',
                                'correct': 'true',
                                'points': 1
                            },
                            {
                                'text': 'What is the main source of light during the day?',
                                'type': 'short_answer',
                                'correct': 'sun',
                                'points': 2
                            }
                        ]
                    }
                }

                for subject_code, exam_data in exams_data.items():
                    exam = Exam.objects.create(
                        title=exam_data['title'],
                        subject=subjects[subject_code],
                        grade_level=exam_data['grade_level'],
                        duration_minutes=exam_data['duration_minutes'],
                        language=exam_data['language'],
                        instructions=exam_data['instructions'],
                        is_active=True,
                        created_by=admin_user
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created exam: {exam.title}'))

                    # Create questions for this exam
                    for i, q_data in enumerate(exam_data['questions'], 1):
                        question = Question.objects.create(
                            exam=exam,
                            question_text=q_data['text'],
                            question_type=q_data['type'],
                            options=q_data.get('options'),
                            correct_answer=q_data['correct'],
                            order=i,
                            points=q_data['points']
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created question {i} for {exam.title}'))

                self.stdout.write(self.style.SUCCESS('Successfully populated exam data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
