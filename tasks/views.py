from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import fonts
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.utils import timezone
from .models import Task, Category
from .forms import RegisterForm, TaskForm, CompletedTaskForm, CategoryForm
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from io import BytesIO
import json


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('daily_tasks')
    else:
        form = RegisterForm()
    return render(request, 'tasks/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('daily_tasks')
        else:
            return render(request, 'tasks/login.html', {'error': 'Invalid credentials'})
    return render(request, 'tasks/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def daily_tasks(request):
    today = date.today()
    tomorrow = today + timedelta(days=1)

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('daily_tasks')
    else:
        form = TaskForm()

    today_tasks = Task.objects.filter(user=request.user, due_date=today, is_deleted=False)
    tomorrow_tasks = Task.objects.filter(user=request.user, due_date=tomorrow, is_deleted=False)

    return render(request, 'tasks/daily_tasks.html', {
        'form': form,
        'today_tasks': today_tasks,
        'tomorrow_tasks': tomorrow_tasks,
        'today': today,
        'tomorrow': tomorrow
    })


@login_required
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        task.is_completed = data['is_completed']
        task.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def completed_tasks(request):
    completed_tasks_list = Task.objects.filter(
        user=request.user,
        is_completed=True,
        is_deleted=False
    ).order_by('-completed_date')

    categories = Category.objects.filter(user=request.user)

    # 筛选逻辑
    category_filter = request.GET.get('category')
    date_filter = request.GET.get('date')

    if category_filter:
        completed_tasks_list = completed_tasks_list.filter(category__id=category_filter)
    if date_filter:
        completed_tasks_list = completed_tasks_list.filter(completed_date=date_filter)

    return render(request, 'tasks/completed_tasks.html', {
        'tasks': completed_tasks_list,
        'categories': categories
    })


@login_required
def edit_completed_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        form = CompletedTaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            form.save()
            return redirect('completed_tasks')
    else:
        form = CompletedTaskForm(instance=task)

    return render(request, 'tasks/edit_completed_task.html', {'form': form})


@login_required
def recycle_bin(request):
    deleted_tasks = Task.objects.filter(user=request.user, is_deleted=True)
    return render(request, 'tasks/recycle_bin.html', {'tasks': deleted_tasks})


@login_required
def export_tasks_pdf(request):
    # 注册中文字体（确保字体文件存在）
    try:
        # 使用系统字体路径或提供自己的字体文件
        pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))
        fonts.addMapping('SimSun', 0, 0, 'SimSun')  # normal
        fonts.addMapping('SimSun', 0, 1, 'SimSun')  # italic
        fonts.addMapping('SimSun', 1, 0, 'SimSun')  # bold
    except:
        # 如果系统字体不可用，可以打包字体文件到项目中
        import os
        from django.conf import settings
        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'simsun.ttc')
        pdfmetrics.registerFont(TTFont('SimSun', font_path))
        fonts.addMapping('SimSun', 0, 0, 'SimSun')

    # 获取筛选条件
    category_filter = request.GET.get('category')
    date_filter = request.GET.get('date')

    # 查询任务
    tasks = Task.objects.filter(
        user=request.user,
        is_completed=True,
        is_deleted=False
    )

    if category_filter:
        tasks = tasks.filter(category__id=category_filter)
    if date_filter:
        tasks = tasks.filter(completed_date=date_filter)

    # 创建PDF
    buffer = BytesIO()

    # 使用支持中文的字体创建文档
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    # 定义样式
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ChineseStyle',
                              fontName='SimSun',
                              fontSize=12,
                              leading=14))

    # 准备内容
    elements = []

    # 标题
    title = Paragraph("Report", styles['Title'])
    elements.append(title)
    elements.append(Paragraph("<br/>", styles['ChineseStyle']))

    # 表格数据
    data = [['任务名称', '完成日期', '用时', '分类', '个人感受']]

    for task in tasks:
        data.append([
            Paragraph(task.title, styles['ChineseStyle']),
            Paragraph(str(task.completed_date), styles['ChineseStyle']),
            Paragraph(str(task.time_spent) if task.time_spent else '-', styles['ChineseStyle']),
            Paragraph(task.category.name if task.category else '-', styles['ChineseStyle']),
            Paragraph(task.reflection if task.reflection else '-', styles['ChineseStyle'])
        ])

    # 创建表格
    table = Table(data, colWidths=[100, 80, 60, 80, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # 构建PDF
    doc.build(elements)

    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="tasks_report.pdf"'
    return response


@login_required
def manage_categories(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect('manage_categories')
    else:
        form = CategoryForm()

    categories = Category.objects.filter(user=request.user)
    return render(request, 'tasks/manage_categories.html', {
        'form': form,
        'categories': categories
    })