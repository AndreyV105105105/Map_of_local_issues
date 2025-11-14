def app_namespace(request):
    resolver = request.resolver_match
    if resolver:
        return {
            'current_namespace': resolver.namespace or resolver.app_name or 'users'
        }
    return {'current_namespace': 'users'}