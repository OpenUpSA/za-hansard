from datetime import datetime
import json

from za_hansard.importers.import_base import ImportZAMixin
from speeches.importers.import_base import ImporterBase
from speeches.models import Section, Speech, Tag

#{
# "parent_section_titles": [
#  "Top Section",
#  "Middle Section",
#  "Bottom Section"
# ],
# "speeches": [
#  {
#   "personname": "M Johnson",
#   "party": "ANC",
#   "text": "Mr M Johnson (ANC) chaired the meeting."
#  },
#  ...
# ],
# "public": true,
# "date": "2013-06-21",
# "organization": "Agriculture, Forestry and Fisheries",
# "reporturl": "http://www.pmg.org.za/report/20130621-report-back-from-departments-health-trade-and-industry-and-agriculture-forestry-and-fisheries-meat-inspection",
# "title": "Report back from Departments of Health, Trade and Industry, and Agriculture, Forestry and Fisheries on meat inspection services and labelling in South Africa",
## "committeeurl": "http://www.pmg.org.za/committees/Agriculture,%20Forestry%20and%20Fisheries"
#}

class ImportJson (ImportZAMixin, ImporterBase):
    def __init__(self, **kwargs):
        super(ImportJson, self).__init__(**kwargs)
        self.delete_existing = kwargs.get('delete_existing', False)

    def import_document(self, document_path, limit=0):

        data = json.load( open(document_path, 'r') )

        start_date_string = data.get( 'date', None )
        start_date = None
        if start_date_string:
            start_date = self.format_date(start_date_string)

        self.set_resolver_for_date(date=start_date)

        self.title = data.get( 'title', data.get('organization', '') )

        # Determine if speeches should be public
        speeches_premium = data.get('premium', False)
        speeches_public = data.get('public', not speeches_premium)

        report_url = data.get('report_url', '')

        # Create parents as needed using parent_section_titles
        parent_section_titles = data.get('parent_section_titles', [])
        parent_section_titles.append(self.title)
        if self.commit:
            section = Section.objects.get_or_create_with_parents(
                instance=self.instance,
                titles=parent_section_titles
            )

        if self.delete_existing and self.commit:
            section.speech_set.all().delete()

        for s in data.get( 'speeches', [] ):

            display_name = s['personname']
            party = s.get('party', '')

            speaker = self.get_person( display_name, party )

            if party:
                display_name += ' (%s)' % party

            if limit and section.speech_set.count() >= limit:
                break

            speech_start_date_string = s.get('date', None)
            speech_start_date = start_date
            if speech_start_date_string:
                speech_start_date = self.format_date(start_date_string)

            speech = self.make(Speech,
                    text = s['text'],
                    section = section,

                    speaker = speaker,
                    speaker_display = display_name,

                    public = speeches_public,

                    location = s.get('location', ''),
                    title    = s.get('title', ''),
                    event    = s.get('event', ''),
                    source_url = s.get('source_url', report_url),

                    # Assume that the speech does not span several days
                    start_date = speech_start_date,
                    end_date   = speech_start_date,

                    # Time not implemented in JSON, but could easily be. For now set to None
                    start_time = None,
                    end_time   = None,
            )

            for tagname in s.get('tags', []):
                if self.commit:
                    (tag,_) = Tag.objects.get_or_create( name=tagname, instance=self.instance )
                    speech.tags.add(tag)

        return section

    def format_date(self, date_string):
        return datetime.strptime( date_string, '%Y-%m-%d' ).date()
