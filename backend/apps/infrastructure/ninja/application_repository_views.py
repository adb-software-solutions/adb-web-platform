from django.http import HttpRequest
from ninja import Router

from apps.infrastructure.models import ApplicationProfile, ApplicationRepositoryLink
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .data_application_schemas import ApplicationRepositoryLinkOut
from .specialist_views import StaffProblem, _permission_problem, _problem

application_repository_router = Router(tags=["admin-infrastructure-application-repositories"])


def _link_out(link: ApplicationRepositoryLink) -> ApplicationRepositoryLinkOut:
    return ApplicationRepositoryLinkOut(
        id=link.id,
        repository_resource_id=link.repository.resource_id,
        repository_name=link.repository.resource.name,
        role=link.role,
        path=link.path,
        notes=link.notes,
    )


@application_repository_router.get(
    "/infrastructure/applications/{resource_id}/repository-links",
    response={
        200: list[ApplicationRepositoryLinkOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_application_repository_links(
    request: HttpRequest,
    resource_id: int,
) -> list[ApplicationRepositoryLinkOut] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_applicationprofile",
        "infrastructure.view_sourcerepository",
        "infrastructure.view_applicationrepositorylink",
    )
    if problem:
        return problem

    visible = scope_infrastructure_resources_for_user(request.user)
    application = (
        ApplicationProfile.objects.select_related("resource")
        .filter(resource__in=visible, resource_id=resource_id)
        .first()
    )
    if application is None:
        return _problem(404, "Application not found.", "not_found")

    links = ApplicationRepositoryLink.objects.select_related("repository__resource").filter(
        application=application,
        repository__resource__in=visible,
    )
    return [_link_out(link) for link in links]
