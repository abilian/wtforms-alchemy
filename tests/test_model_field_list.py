import sqlalchemy as sa
from wtforms_alchemy import ModelForm, ModelFieldList
from wtforms_components import PassiveHiddenField
from wtforms.fields import FormField
from tests import FormRelationsTestCase, MultiDict


class ModelFieldListTestCase(FormRelationsTestCase):
    def create_models(self):
        class Event(self.base):
            __tablename__ = 'event'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)

        class Location(self.base):
            __tablename__ = 'location'
            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=True)

            event_id = sa.Column(sa.Integer, sa.ForeignKey(Event.id))
            event = sa.orm.relationship(Event, backref='locations')

        self.Event = Event
        self.Location = Location

    def save(self, event=None, data={}):
        if not data:
            data = {
                'name': u'Some event',
                'locations-0-name': u'Some location',
            }
        if not event:
            event = self.Event()
            self.session.add(event)
        form = self.EventForm(MultiDict(data))
        form.validate()
        form.populate_obj(event)
        self.session.commit()
        return event


class TestReplaceStrategy(ModelFieldListTestCase):
    def create_forms(self):
        class LocationForm(ModelForm):
            class Meta:
                model = self.Location

        class EventForm(ModelForm):
            class Meta:
                model = self.Event

            locations = ModelFieldList(FormField(LocationForm))

        self.LocationForm = LocationForm
        self.EventForm = EventForm

    def test_assigment_and_deletion(self):
        self.save()
        event = self.session.query(self.Event).first()
        assert event.locations[0].name == u'Some location'
        data = {
            'name': u'Some event'
        }
        form = self.EventForm(MultiDict(data))
        form.validate()
        form.populate_obj(event)
        self.session.commit()
        event = self.session.query(self.Event).first()
        assert event.locations == []


class TestUpdateStrategy(ModelFieldListTestCase):
    def create_models(self):
        class Event(self.base):
            __tablename__ = 'event'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)

        class Location(self.base):
            __tablename__ = 'location'
            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=True)

            event_id = sa.Column(sa.Integer, sa.ForeignKey(Event.id))
            event = sa.orm.relationship(Event, backref='locations')

            def __repr__(self):
                return 'Location(id=%r, name=%r)' % (self.id, self.name)

        self.Event = Event
        self.Location = Location

    def create_forms(self):
        class LocationForm(ModelForm):
            class Meta:
                model = self.Location

            id = PassiveHiddenField()

        class EventForm(ModelForm):
            class Meta:
                model = self.Event

            locations = ModelFieldList(
                FormField(LocationForm),
                population_strategy='update'
            )

        self.LocationForm = LocationForm
        self.EventForm = EventForm

    def test_single_entry_update(self):
        event = self.save()
        location_id = event.locations[0].id
        data = {
            'name': u'Some event',
            'locations-0-id': location_id,
            'locations-0-name': u'Some other location'
        }
        self.save(event, data)

        assert event.locations[0].id == location_id
        assert event.locations[0].name == u'Some other location'

    def test_skips_entries_with_unknown_identifiers(self):
        event = self.save()
        data = {
            'name': u'Some event',
            'locations-0-id': 12,
            'locations-0-name': u'Some other location'
        }
        self.save(event, data)
        assert not event.locations

    def test_replace_entry(self):
        event = self.save()
        location_id = event.locations[0].id
        data = {
            'name': u'Some event',
            'locations-0-name': u'Some location',
        }
        self.save(event, data)
        assert event.locations[0].id == location_id + 1
        assert len(event.locations) == 1

    def test_multiple_entries(self):
        event = self.save()
        location_id = event.locations[0].id
        data = {
            'name': u'Some event',
            'locations-0-name': u'Some location',
            'locations-1-id': str(location_id),  # test coercing works
            'locations-1-name': u'Some other location',
            'locations-2-name': u'Third location',
            'locations-3-id': 123,
            'locations-3-name': u'Fourth location'
        }
        self.save(event, data)
        assert len(event.locations) == 3
        names = [location.name for location in event.locations]
        assert 'Some location' in names
        assert 'Some other location' in names
        assert 'Third location' in names
