from django.shortcuts import render, redirect, reverse


def home_view(request):
    return render(request, 'polygon/home.jinja2', context={'polygon_authorized': True})
    # TODO: polygon authorization


def register_view(request):
    template_name = 'polygon/register.jinja2'
    if request.method == 'GET':
        return render(request, template_name)
    else:
        if request.POST.get('terms') != 'on':
            return render(request, template_name, context={'register_error': 'You did\'nt accept terms of use.'})
        # TODO: or not authorized:
        request.user.polygon_enabled = True
        request.user.save(update_fields=['polygon_enabled'])
        return redirect(reverse('polygon:home'))
