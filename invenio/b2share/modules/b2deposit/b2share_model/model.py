## This file is part of B2SHARE.
## Copyright (C) 2013 EPCC, The University of Edinburgh.
##
## B2SHARE is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## B2SHARE is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with B2SHARE; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import collections
import csv
import os.path

from invenio.ext.sqlalchemy import db
from flask import current_app
from datetime import date

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


class FieldSet:
    def __init__(self, name, basic_fields=[], optional_fields=[]):
        self.name = name
        self.basic_fields = basic_fields
        self.optional_fields = optional_fields


class SubmissionMetadata(db.Model):
    """DataCite-based metadata class. Format description is here:
    http://schema.datacite.org/meta/kernel-2.2/doc/DataCite-MetadataKernel_v2.2.pdf
    """
    __tablename__ = 'submission_metadata'
    domain = 'Generic'
    icon = 'icon-question-sign'
    kind = 'domain'
    field_args = {}
    publisher_default = current_app.config.get('CFG_SITE_URL')
    publication_date_now = date.today()
    language_default = 'en'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text(), nullable=False)
    creator = db.Column(db.String(256))
    title = db.Column(db.String(256), nullable=False)
    open_access = db.Column(db.Boolean(), default=True)
    embargo_till = db.Column(db.String(128))

    licence = db.Column(db.String(128))  # note we set licences in __init__
    publisher = db.Column(db.String(128), default=publisher_default)
    publication_date = db.Column('publication_year', db.Date(), default=publication_date_now)
    keywords = db.Column(db.String(256))  # split on ,
    discipline = db.Column(db.String(256))

    # optional
    contributors = db.Column(db.String(256))
    # language = db.Column(db.Enum(*babel.core.LOCALE_ALIASES.keys()))
    language = db.Column(db.String(128), default=language_default)
    resource_type = db.Column(db.String(256))  # XXX should be extracted to a separate class
    alternate_identifier = db.Column(db.String(256))
    version = db.Column(db.String(128))
    contact_email = db.Column(db.String(256))

    basic_fields = ['title', 'description', 'creator', 'open_access',
                    'embargo_till', 'licence', 'publication_date',
                    'keywords', 'contact_email', 'discipline', ]
    optional_fields = ['contributors', 'resource_type', 'alternate_identifier',
                       'version', 'publisher', 'language', ]

    # using joined table inheritance for the specific domains
    submission_type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_identity': 'generic',
        'polymorphic_on': submission_type
    }

    def __repr__(self):
        return '<SubmissionMetadata %s>' % self.id

    def __init__(self):
        self.fieldsets = [(FieldSet("Generic",
                                    basic_fields=self.basic_fields,
                                    optional_fields=self.optional_fields))]
        self.field_args['title'] = {
            'placeholder': "Title of the resource",
            'description': 'The title of the uploaded resource - a name '
                           'that indicates the content to be expected.'
        }
        self.field_args['description'] = {
            'description': 'A more elaborate description of the resource. '
                           'Focus on a description of content making it '
                           'easy for others to find it and to interpret '
                           'its relevance quickly.'
        }
        self.field_args['publisher'] = {
            'value': self.publisher_default,
            'description': 'The entity responsible for making the resource '
                           'available, either a person, an organization, or '
                           'a service.'
        }
        self.field_args['publication_date'] = {
            'hidden': True,
            'value': self.publication_date_now
            # 'description':
            # 'This is the date that the resource was uploaded and thus '
            # 'being available broadly. Also this date can be extracted '
            # 'automatically.'
        }
        self.field_args['version'] = {
            'placeholder': 'e.g. v1.02',
            'description': 'Denote the version of the resource.'
        }
        self.field_args['licence'] = {
            'description': 'Specify the license under which this data set '
                           'is available to the users (e.g. GPL, Apache v2 '
                           'or Commercial). Please use the License Selector '
                           'for help and additional information.'
        }
        self.field_args['keywords'] = {
            'placeholder': "keyword1, keyword2, ...",
            'cardinality': 'n',
            'description': 'A comma separated list of keywords that '
                           'characterize the content.'
        }
        self.field_args['open_access'] = {
            'description': 'Indicate whether the resource is open or '
                           'access is restricted. In case of restricted '
                           'access the uploaded files will not be public, '
                           'however the metadata will be.'
        }
        self.field_args['embargo_till'] = {
            #'placeholder': 'Embargo end date',
            'description': 'Submitted files are hidden under embargo and will '
                           'become accessible the day the embargo ends'
        }
        self.field_args['contributors'] = {
            'placeholder': 'contributor',
            'cardinality': 'n',
            'description': 'A semicolon separated list of all other '
                           'contributors. Mention all other persons that '
                           'were relevant in the creation of the resource.'
        }
        self.field_args['language'] = {
            'value': self.language_default,
            'description': 'The name of the language the document is written in.'
        }
        self.field_args['resource_type'] = {
            'data_provide': 'select',
            'cardinality': 'n',
            'data_source': ['Text', 'Image', 'Video', 'Audio', 'Time-Series', 'Other'],
            'description': 'Select the type of the resource.'
        }
        self.field_args['alternate_identifier'] = {
            'placeholder': 'Other reference, such as URI, ISBN, etc.',
            'description': 'Any kind of other reference such as a URN, URI '
                           'or an ISBN number.'
        }
        self.field_args['creator'] = {
            'placeholder': 'author',
            'cardinality': 'n',
            'description': 'The author(s) of the resource.'
        }
        self.field_args['contact_email'] = {
            'placeholder': 'contact email',
            'description': 'Contact email information for this record'
        }
        self.field_args['discipline'] = {
            'data_provide': 'select',
            'cardinality': 'n',
            'data_source': [(d[2], ' / '.join(d)) for d in generate_disciplines()],
            'description': 'Select the discipline of the resource.'
        }


def _create_metadata_class(cfg):
    """Creates domain classes that map form fields to databases plus some other
    details."""

    # The following function and call just add all external attrs manually
    def is_external_attr(n):
        # don't like this bit; problem is we don't want to include the
        # db import and I don't know how to exclude them except via name
        if n in ['db', 'fields']:
            return False

        return not n.startswith('__')

    def __init__(self):
        """
        Init method for the newly created class type
        """
        parent = super(type(self), self)
        parent.__init__()

        if len(cfg.fields) > 0:
            basic_fields = [f['name'] for f in cfg.fields if not f.get('extra')]
            optional_fields = [f['name'] for f in cfg.fields if f.get('extra')]
            basic_intersect = set(basic_fields).intersection(parent.basic_fields)
            optional_intersect = set(optional_fields).intersection(parent.optional_fields)
            basic_dups = [x for x, y in collections.Counter(basic_fields).items() if y > 1]
            optional_dups = [x for x, y in collections.Counter(optional_fields).items() if y > 1]

            if basic_dups:
                raise AttributeError("'{0}' duplicates in basic fields".format(", ".join(basic_dups)))
            if optional_dups:
                raise AttributeError("'{0}' duplicates in optional fields".format(", ".join(optional_dups)))
            if basic_intersect:
                raise AttributeError("'{0}' conflicts in basic fields".format(", ".join(basic_intersect)))
            if optional_intersect:
                raise AttributeError("'{0}' conflicts in optional fields".format(", ".join(optional_intersect)))

            self.fieldsets.append(
                FieldSet(cfg.domain,
                         basic_fields=basic_fields,
                         optional_fields=optional_fields))

    if not hasattr(cfg, 'fields'):
        cfg.fields = []

    clsname = cfg.domain + "Metadata"

    args = {'__init__': __init__,
            '__tablename__': cfg.table_name,
            '__mapper_args__': {'polymorphic_identity': cfg.table_name},
            'id': db.Column(db.Integer,
                            db.ForeignKey('submission_metadata.id'),
                            primary_key=True),
            'field_args': {}}

    for attr in (filter(is_external_attr, dir(cfg))):
        args[attr] = getattr(cfg, attr)

    # field args lets us control some aspects of the field
    # including label, validators and decimal places
    for f in cfg.fields:
        nullable = not f.get('required', False)
        args[f['name']] = db.Column(f['col_type'], nullable=nullable)
        field_dict = {}
        for k in f:
            if k in ['description', 'data_provide', 'data_source', 'default',
                     'placeholder', 'value', 'other', 'cardinality']:
                field_dict[k] = f.get(k)
            elif k == 'display_text':
                field_dict['label'] = f.get(k)
        args['field_args'][f['name']] = field_dict

    return type(clsname, (SubmissionMetadata,), args)


def generate_disciplines():
    """
    Generator function that produces disciplines from a CSV file
    """
    with open(os.path.join(CURRENT_DIR, 'disciplines.tab')) as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header
        for line in reader:
            yield [l.strip() for l in line]  # Clean values

class Bib98x(db.Model):
    """Represents a Bib98x record."""
    def __init__(self):
        pass
    __tablename__ = 'bib98x'
    id = db.Column(db.MediumInteger(8, unsigned=True),
                primary_key=True,
                autoincrement=True)
    tag = db.Column(db.String(6), nullable=False, index=True,
                server_default='')
    value = db.Column(db.Text(35), nullable=False,
                index=True)


class BibrecBib98x(db.Model):
    """Represents a BibrecBib98x record."""
    def __init__(self):
        pass
    from invenio.modules.records.models import Record as Bibrec
    __tablename__ = 'bibrec_bib98x'
    id_bibrec = db.Column(db.MediumInteger(8, unsigned=True),
                db.ForeignKey(Bibrec.id),
        nullable=False, primary_key=True, index=True,
                server_default='0')
    id_bibxxx = db.Column(db.MediumInteger(8, unsigned=True),
                db.ForeignKey(Bib98x.id),
        nullable=False, primary_key=True, index=True,
                server_default='0')
    field_number = db.Column(db.SmallInteger(5, unsigned=True),
                primary_key=True)
    bibrec = db.relationship(Bibrec, backref='bib98xs')
    bibxxx = db.relationship(Bib98x, backref='bibrecs')
