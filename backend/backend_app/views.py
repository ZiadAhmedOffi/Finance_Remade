from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

# Create your views here.
def home(request):
    return HttpResponse('This is the home page')

def ping(request):
    return JsonResponse({'status': 'ok'})