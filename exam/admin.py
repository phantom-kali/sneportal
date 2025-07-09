from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .models import Subject, Exam, Question, ExamSession, StudentResponse


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'exam_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at']

    def exam_count(self, obj):
        return obj.exam_set.count()
    exam_count.short_description = 'Number of Exams'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            exam_count=Count('exam')
        )


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['order', 'question_text', 'question_type', 'correct_answer', 'points']
    readonly_fields = []
    
    def get_max_num(self, request, obj=None, **kwargs):
        return 50  # Limit max questions per exam


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'grade_level', 'duration_minutes', 'question_count', 'total_points', 'is_active', 'created_at']
    list_filter = ['subject', 'grade_level', 'is_active', 'language', 'created_at']
    search_fields = ['title', 'subject__name', 'instructions']
    readonly_fields = ['created_at', 'question_count', 'total_points']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'grade_level', 'language', 'is_active')
        }),
        ('Exam Settings', {
            'fields': ('duration_minutes', 'instructions')
        }),
        ('Statistics', {
            'fields': ('question_count', 'total_points', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def question_count(self, obj):
        return obj.get_total_questions()
    question_count.short_description = 'Questions'

    def total_points(self, obj):
        return obj.get_total_points()
    total_points.short_description = 'Total Points'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject', 'created_by')

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'order', 'question_preview', 'question_type', 'points']
    list_filter = ['exam', 'question_type', 'points']
    search_fields = ['question_text', 'exam__title']
    ordering = ['exam', 'order']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('exam', 'order', 'question_text', 'question_type', 'points')
        }),
        ('Answer Options', {
            'fields': ('options', 'correct_answer'),
            'description': 'For multiple choice, use JSON format: {"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"}'
        }),
    )

    def question_preview(self, obj):
        return obj.question_text[:100] + "..." if len(obj.question_text) > 100 else obj.question_text
    question_preview.short_description = 'Question Text'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exam')


class StudentResponseInline(admin.TabularInline):
    model = StudentResponse
    extra = 0
    readonly_fields = ['question', 'transcribed_text', 'final_answer', 'is_correct', 'points_earned', 'answered_at']
    fields = ['question', 'final_answer', 'is_correct', 'points_earned', 'answered_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student_name', 'student_grade', 'current_state', 'progress', 'score_display', 'time_remaining_display', 'started_at']
    list_filter = ['exam', 'current_state', 'started_at', 'completed_at']
    search_fields = ['student_name', 'exam__title']
    readonly_fields = ['session_id', 'started_at', 'completed_at', 'progress_percentage', 'score_display']
    inlines = [StudentResponseInline]
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student_name', 'student_grade')
        }),
        ('Exam Details', {
            'fields': ('exam', 'session_id', 'current_state', 'current_question_index')
        }),
        ('Progress & Scoring', {
            'fields': ('progress_percentage', 'total_score', 'score_display', 'time_remaining')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def progress(self, obj):
        return f"{obj.progress_percentage:.1f}%"
    progress.short_description = 'Progress'

    def score_display(self, obj):
        total_possible = obj.exam.get_total_points()
        return f"{obj.total_score}/{total_possible}"
    score_display.short_description = 'Score'

    def time_remaining_display(self, obj):
        if obj.time_remaining <= 0:
            return format_html('<span style="color: red;">Time Up</span>')
        elif obj.time_remaining <= 300:  # 5 minutes
            return format_html('<span style="color: orange;">{}</span>', obj.time_remaining_formatted)
        return obj.time_remaining_formatted
    time_remaining_display.short_description = 'Time Remaining'

    def has_add_permission(self, request):
        return False  # Sessions created through voice interface only

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exam', 'exam__subject')


@admin.register(StudentResponse)
class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ['exam_session', 'question_preview', 'final_answer', 'is_correct', 'points_earned', 'answered_at']
    list_filter = ['is_correct', 'question__question_type', 'answered_at']
    search_fields = ['exam_session__student_name', 'question__question_text', 'final_answer']
    readonly_fields = ['exam_session', 'question', 'transcribed_text', 'answered_at', 'is_correct', 'points_earned']
    
    fieldsets = (
        ('Response Details', {
            'fields': ('exam_session', 'question', 'final_answer', 'attempts')
        }),
        ('Voice Processing', {
            'fields': ('audio_file', 'transcribed_text'),
            'classes': ('collapse',)
        }),
        ('Scoring', {
            'fields': ('is_correct', 'points_earned', 'answered_at')
        }),
    )

    def question_preview(self, obj):
        return f"Q{obj.question.order}: {obj.question.question_text[:50]}..."
    question_preview.short_description = 'Question'

    def has_add_permission(self, request):
        return False  # Responses created through voice interface only

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exam_session', 'question')


# Custom admin site configuration
admin.site.site_header = 'Voice Exam System Administration'
admin.site.site_title = 'Voice Exam Admin'
admin.site.index_title = 'Welcome to Voice Exam System Administration'