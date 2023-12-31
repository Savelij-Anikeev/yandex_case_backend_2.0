from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework import viewsets, status
from django.contrib.auth.models import User
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import UserSerializer, EventSerializer, UserEventRelSerializer
from .models import Event, UserEventRel

from django.conf import settings
from .permissions import IsOwnerOrAdmin

from file_uploader_app.storage_scripts import upload_event

from mailing_app import logic


class UserViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    crud operations with `Event` model
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = ()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response({'detail': 'created'}, status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        checking if it`s place limited
        """

        if serializer.validated_data['is_place_limited']:
            serializer.validated_data['free_places'] = serializer.validated_data['places']
        else:
            serializer.validated_data['free_places'] = serializer.validated_data['places'] = 0

        #   changing photo if it is not there
        if not serializer.validated_data['photo']:
            serializer.validated_data['photo_url'] = settings.DEFAULT_IMG_URL

            serializer.save()
            return

        #
        if serializer.validated_data['photo_url'] != '':
            serializer.validated_data['photo'] = None

            serializer.save()
            return
        obj = serializer.save()
        upload_event.delay(obj.id)

    def get_queryset(self):
        """
        returning queryset and changing
        it if there are `GET` params
        """

        if 'is_verified' in self.request.GET:
            """looking for get param"""
            if self.request.GET['is_verified'] == 'False':
                return Event.objects.filter(is_verified=False)
            if self.request.GET['is_verified'] == 'all':
                return Event.objects.all()
        return Event.objects.filter(is_verified=True)

    def get_permissions(self):
        """
        letting do crud operations with event if
        user have permissions
        """

        if self.request.method not in ('GET', 'POST', 'HEAD', 'OPTIONS'):
            permission_classes = (IsAuthenticated, IsOwnerOrAdmin)
        else:
            permission_classes = ()
        return [permission() for permission in permission_classes]


class UserEventRelViewSet(viewsets.ModelViewSet):
    """
    describes behavior of relations between
    `User` and `Event`
    """

    queryset = UserEventRel.objects.all()
    serializer_class = UserEventRelSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """
        finding relation by `Event` id
        """

        event_id = self.kwargs['pk']
        obj = get_object_or_404(UserEventRel,
                                event=get_object_or_404(Event, id=event_id),
                                user=self.request.user)
        return obj

    def perform_create(self, serializer):
        """
        automatically adding user
        """

        curr_user = self.request.user
        curr_event = get_object_or_404(Event, id=self.request.data['event'])
        serializer.validated_data['user'] = curr_user
        serializer.validated_data['event'] = curr_event

        # checking if relation exists
        if len(UserEventRel.objects.filter(event=curr_event, user=curr_user)) != 0:
            return self.perform_update(serializer)
        serializer.save()

        # counting free places
        qs = Event.objects.filter(id=curr_event.id)
        if qs[0].is_place_limited:
            qs.update(free_places=F('free_places')-1)

    def perform_destroy(self, instance):
        """
        counting free places
        """

        instance.delete()

        # counting free places
        qs = Event.objects.filter(id=instance.id)
        if qs[0].is_place_limited:
            qs.update(free_places=F('free_places')+1)

    def get_queryset(self):
        """
        list only relation user in
        """

        if self.request.user.is_authenticated:
            return UserEventRel.objects.filter(user=self.request.user)
        return UserEventRel.objects.none()


@receiver(post_save, sender=UserEventRel)
def send_mail_on_create(sender, instance, created=False, **kwargs):
    if created:
        logic.send_to_defined_person.delay(instance_id=instance.id)
        # send_to_defined_person()
