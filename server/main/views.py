from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, "index.html")

def bookView(request):
    return render(request, "main/book.html")