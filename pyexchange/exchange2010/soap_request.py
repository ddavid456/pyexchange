"""
(c) 2013 LinkedIn Corp. All rights reserved.
Licensed under the Apache License, Version 2.0 (the "License");?you may not use this file except in compliance with the License. You may obtain a copy of the License at  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software?distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
from lxml.builder import ElementMaker
from ..utils import convert_datetime_to_utc, convert_to_win32time
from ..compat import _unicode

MSG_NS = u'http://schemas.microsoft.com/exchange/services/2006/messages'
TYPE_NS = u'http://schemas.microsoft.com/exchange/services/2006/types'
SOAP_NS = u'http://schemas.xmlsoap.org/soap/envelope/'

soap = ElementMaker(namespace='http://schemas.xmlsoap.org/soap/envelope/', nsmap={
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'm': 'http://schemas.microsoft.com/exchange/services/2006/messages',
    't': 'http://schemas.microsoft.com/exchange/services/2006/types',
    'soap': 'http://schemas.xmlsoap.org/soap/envelope/'
})

NAMESPACES = {u'm': MSG_NS, u't': TYPE_NS, u's': SOAP_NS}

M = ElementMaker(namespace=MSG_NS, nsmap=NAMESPACES)
T = ElementMaker(namespace=TYPE_NS, nsmap=NAMESPACES)

EXCHANGE_DATETIME_FORMAT = u"%Y-%m-%dT%H:%M:%SZ"
EXCHANGE_DATE_FORMAT = u"%Y-%m-%d"

DISTINGUISHED_IDS = (
  'calendar', 'contacts', 'deleteditems', 'drafts', 'inbox', 'journal', 'notes', 'outbox', 'sentitems',
  'tasks', 'msgfolderroot', 'root', 'junkemail', 'searchfolders', 'voicemail', 'recoverableitemsroot',
  'recoverableitemsdeletions', 'recoverableitemsversions', 'recoverableitemspurges', 'archiveroot',
  'archivemsgfolderroot', 'archivedeleteditems', 'archiverecoverableitemsroot',
  'Archiverecoverableitemsdeletions', 'Archiverecoverableitemsversions', 'Archiverecoverableitemspurges',
)


def exchange_header():

  return T.RequestServerVersion({u'Version': u'Exchange2010'})


def resource_node(element, resources):
  """
  Helper function to generate a person/conference room node from an email address

  <t:OptionalAttendees>
    <t:Attendee>
        <t:Mailbox>
            <t:EmailAddress>{{ attendee_email }}</t:EmailAddress>
        </t:Mailbox>
    </t:Attendee>
  </t:OptionalAttendees>
  """

  for attendee in resources:
    element.append(
      T.Attendee(
        T.Mailbox(
          T.EmailAddress(attendee.email)
        )
      )
    )

  return element


def delete_field(field_uri):
  """
      Helper function to request deletion of a field. This is necessary when you want to overwrite values instead of
      appending.

      <t:DeleteItemField>
        <t:FieldURI FieldURI="calendar:Resources"/>
      </t:DeleteItemField>
  """

  root = T.DeleteItemField(
    T.FieldURI(FieldURI=field_uri)
  )

  return root


def get_item(exchange_id, format=u"Default"):
  """
    Requests a calendar item from the store.

    exchange_id is the id for this event in the Exchange store.

    format controls how much data you get back from Exchange. Full docs are here, but acceptible values
    are IdOnly, Default, and AllProperties.

    http://msdn.microsoft.com/en-us/library/aa564509(v=exchg.140).aspx

    <m:GetItem  xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
            xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <m:ItemShape>
          <t:BaseShape>{format}</t:BaseShape>
      </m:ItemShape>
      <m:ItemIds>
          <t:ItemId Id="{exchange_id}"/>
      </m:ItemIds>
  </m:GetItem>

  """

  elements = list()
  if type(exchange_id) == list:
    for item in exchange_id:
      elements.append(T.ItemId(Id=item))
  else:
    elements = [T.ItemId(Id=exchange_id)]

  root = M.GetItem(
    M.ItemShape(
      T.BaseShape(format)
    ),
    M.ItemIds(
      *elements
    )
  )
  return root

def get_calendar_items(format=u"Default", calendar_id=u'calendar', start=None, end=None, max_entries=999999, delegate_for=None):
  start = start.strftime(EXCHANGE_DATETIME_FORMAT)
  end = end.strftime(EXCHANGE_DATETIME_FORMAT)

  if calendar_id == u'calendar':
    if delegate_for is None:
      target = M.ParentFolderIds(T.DistinguishedFolderId(Id=calendar_id))
    else:
      target = M.ParentFolderIds(
        T.DistinguishedFolderId(
          {'Id': 'calendar'},
          T.Mailbox(T.EmailAddress(delegate_for))
        )
      )
  else:
    target = M.ParentFolderIds(T.FolderId(Id=calendar_id))

  root = M.FindItem(
    {u'Traversal': u'Shallow'},
    M.ItemShape(
      T.BaseShape(format)
    ),
    M.CalendarView({
      u'MaxEntriesReturned': _unicode(max_entries),
      u'StartDate': start,
      u'EndDate': end,
    }),
    target,
  )

  return root


def get_master(exchange_id, format=u"Default"):
  """
    Requests a calendar item from the store.

    exchange_id is the id for this event in the Exchange store.

    format controls how much data you get back from Exchange. Full docs are here, but acceptible values
    are IdOnly, Default, and AllProperties.

    http://msdn.microsoft.com/en-us/library/aa564509(v=exchg.140).aspx

    <m:GetItem  xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
            xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <m:ItemShape>
          <t:BaseShape>{format}</t:BaseShape>
      </m:ItemShape>
      <m:ItemIds>
          <t:RecurringMasterItemId OccurrenceId="{exchange_id}"/>
      </m:ItemIds>
  </m:GetItem>

  """

  root = M.GetItem(
    M.ItemShape(
      T.BaseShape(format)
    ),
    M.ItemIds(
      T.RecurringMasterItemId(OccurrenceId=exchange_id)
    )
  )
  return root


def get_occurrence(exchange_id, instance_index, format=u"Default"):
  """
    Requests one or more calendar items from the store matching the master & index.

    exchange_id is the id for the master event in the Exchange store.

    format controls how much data you get back from Exchange. Full docs are here, but acceptible values
    are IdOnly, Default, and AllProperties.

    GetItem Doc:
    http://msdn.microsoft.com/en-us/library/aa564509(v=exchg.140).aspx
    OccurrenceItemId Doc:
    http://msdn.microsoft.com/en-us/library/office/aa580744(v=exchg.150).aspx

    <m:GetItem  xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
            xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <m:ItemShape>
          <t:BaseShape>{format}</t:BaseShape>
      </m:ItemShape>
      <m:ItemIds>
        {% for index in instance_index %}
          <t:OccurrenceItemId RecurringMasterId="{exchange_id}" InstanceIndex="{{ index }}"/>
        {% endfor %}
      </m:ItemIds>
    </m:GetItem>
  """

  root = M.GetItem(
    M.ItemShape(
      T.BaseShape(format)
    ),
    M.ItemIds()
  )

  items_node = root.xpath("//m:ItemIds", namespaces=NAMESPACES)[0]
  for index in instance_index:
    items_node.append(T.OccurrenceItemId(RecurringMasterId=exchange_id, InstanceIndex=str(index)))
  return root


def get_folder(folder_id, format=u"Default"):

  id = T.DistinguishedFolderId(Id=folder_id) if folder_id in DISTINGUISHED_IDS else T.FolderId(Id=folder_id)

  root = M.GetFolder(
    M.FolderShape(
      T.BaseShape(format)
    ),
    M.FolderIds(id)
  )
  return root


def new_folder(folder):

  id = T.DistinguishedFolderId(Id=folder.parent_id) if folder.parent_id in DISTINGUISHED_IDS else T.FolderId(Id=folder.parent_id)

  if folder.folder_type == u'Folder':
    folder_node = T.Folder(T.DisplayName(folder.display_name))
  elif folder.folder_type == u'CalendarFolder':
    folder_node = T.CalendarFolder(T.DisplayName(folder.display_name))

  root = M.CreateFolder(
    M.ParentFolderId(id),
    M.Folders(folder_node)
  )
  return root


def find_folder(parent_id, format=u"Default"):

  id = T.DistinguishedFolderId(Id=parent_id) if parent_id in DISTINGUISHED_IDS else T.FolderId(Id=parent_id)

  root = M.FindFolder(
    {u'Traversal': u'Shallow'},
    M.FolderShape(
      T.BaseShape(format)
    ),
    M.ParentFolderIds(id)
  )
  return root


def delete_folder(folder):

  root = M.DeleteFolder(
    {u'DeleteType': 'HardDelete'},
    M.FolderIds(
      T.FolderId(Id=folder.id)
    )
  )
  return root


def new_event(event):
  """
  Requests a new event be created in the store.

  http://msdn.microsoft.com/en-us/library/aa564690(v=exchg.140).aspx
  http://docs.microsoft.com/en-us/exchange/client-developer/exchange-web-services/how-to-create-appointments-and-meetings-by-using-ews-in-exchange-2013

  <?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
       xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header>
    <t:RequestServerVersion Version="Exchange2007_SP1" />
    <t:TimeZoneContext>
      <t:TimeZoneDefinition Id="Pacific Standard Time" />
    </t:TimeZoneContext>
  </soap:Header>
  <soap:Body>
    <m:CreateItem SendMeetingInvitations="SendToAllAndSaveCopy">
      <m:Items>
        <t:CalendarItem>
          <t:Subject>Team building exercise</t:Subject>
          <t:Body BodyType="HTML">Let's learn to really work as a team and then have lunch!</t:Body>
          <t:ReminderMinutesBeforeStart>60</t:ReminderMinutesBeforeStart>
          <t:Start>2013-09-21T16:00:00.000Z</t:Start>
          <t:End>2013-09-21T20:00:00.000Z</t:End>
          <t:Location>Conference Room 12</t:Location>
          <t:RequiredAttendees>
            <t:Attendee>
              <t:Mailbox>
                <t:EmailAddress>Mack.Chaves@contoso.com</t:EmailAddress>
              </t:Mailbox>
            </t:Attendee>
            <t:Attendee>
              <t:Mailbox>
                <t:EmailAddress>Sadie.Daniels@contoso.com</t:EmailAddress>
              </t:Mailbox>
            </t:Attendee>
          </t:RequiredAttendees>
          <t:OptionalAttendees>
            <t:Attendee>
              <t:Mailbox>
                <t:EmailAddress>Magdalena.Kemp@contoso.com</t:EmailAddress>
              </t:Mailbox>
            </t:Attendee>
          </t:OptionalAttendees>
          <t:MeetingTimeZone TimeZoneName="Pacific Standard Time" />
        </t:CalendarItem>
      </m:Items>
    </m:CreateItem>
  </soap:Body>
</soap:Envelope>
  """

  envelope = soap('Envelope')
  header = soap('Header')
  body = soap('Body')

  start = convert_datetime_to_utc(event.start)
  end = convert_datetime_to_utc(event.end)
  timezone = convert_to_win32time(event.start)

  header.append(T.RequestServerVersion(Version="Exchange2007_SP1"))
  header.append(T.TimeZoneContext(T.TimeZoneDefinition(Id=timezone)))

  calendar_node = T.CalendarItem(
        T.Subject(event.subject),
        T.Body(event.body or u'', BodyType="HTML"),
      )

  root = M.CreateItem(
    M.Items(
      calendar_node
    ),
    SendMeetingInvitations="SendToAllAndSaveCopy"
  )

  body.append(root)
  envelope.append(header)
  envelope.append(body)

  if event.reminder_minutes_before_start:
    calendar_node.append(T.ReminderIsSet('true'))
    calendar_node.append(T.ReminderMinutesBeforeStart(str(event.reminder_minutes_before_start)))
  else:
    calendar_node.append(T.ReminderIsSet('false'))

  calendar_node.append(T.Start(start.strftime(EXCHANGE_DATETIME_FORMAT)))
  calendar_node.append(T.End(end.strftime(EXCHANGE_DATETIME_FORMAT)))



  if event.is_all_day:
    calendar_node.append(T.IsAllDayEvent('true'))

  if event.location:
    calendar_node.append(T.Location(event.location or u''))


  if event.required_attendees:
    calendar_node.append(resource_node(element=T.RequiredAttendees(), resources=event.required_attendees))

  if event.optional_attendees:
    calendar_node.append(resource_node(element=T.OptionalAttendees(), resources=event.optional_attendees))

  if event.resources:
    calendar_node.append(resource_node(element=T.Resources(), resources=event.resources))

  if event.recurrence:

    if event.recurrence == u'daily':
      recurrence = T.DailyRecurrence(
        T.Interval(str(event.recurrence_interval)),
      )
    elif event.recurrence == u'weekly':
      recurrence = T.WeeklyRecurrence(
        T.Interval(str(event.recurrence_interval)),
        T.DaysOfWeek(event.recurrence_days),
      )
    elif event.recurrence == u'monthly':
      recurrence = T.AbsoluteMonthlyRecurrence(
        T.Interval(str(event.recurrence_interval)),
        T.DayOfMonth(str(event.start.day)),
      )
    elif event.recurrence == u'yearly':
      recurrence = T.AbsoluteYearlyRecurrence(
        T.DayOfMonth(str(event.start.day)),
        T.Month(event.start.strftime("%B")),
      )

    calendar_node.append(
      T.Recurrence(
        recurrence,
        T.EndDateRecurrence(
          T.StartDate(event.start.strftime(EXCHANGE_DATE_FORMAT)),
          T.EndDate(event.recurrence_end_date.strftime(EXCHANGE_DATE_FORMAT)),
        )
      )
    )

  calendar_node.append(T.MeetingTimeZone(TimeZoneName=timezone))
  return envelope


def delete_event(event):
    """

    Requests an item be deleted from the store.


    <DeleteItem
        xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
        xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types"
        DeleteType="HardDelete"
        SendMeetingCancellations="SendToAllAndSaveCopy"
        AffectedTaskOccurrences="AllOccurrences">
            <ItemIds>
                <t:ItemId Id="{{ id }}" ChangeKey="{{ change_key }}"/>
            </ItemIds>
    </DeleteItem>

    """
    root = M.DeleteItem(
      M.ItemIds(
        T.ItemId(Id=event.id, ChangeKey=event.change_key)
      ),
      DeleteType="HardDelete",
      SendMeetingCancellations="SendToAllAndSaveCopy",
      AffectedTaskOccurrences="AllOccurrences"
    )

    return root


def move_event(event, folder_id):

  id = T.DistinguishedFolderId(Id=folder_id) if folder_id in DISTINGUISHED_IDS else T.FolderId(Id=folder_id)

  root = M.MoveItem(
    M.ToFolderId(id),
    M.ItemIds(
        T.ItemId(Id=event.id, ChangeKey=event.change_key)
    )
  )
  return root


def move_folder(folder, folder_id):

  id = T.DistinguishedFolderId(Id=folder_id) if folder_id in DISTINGUISHED_IDS else T.FolderId(Id=folder_id)

  root = M.MoveFolder(
    M.ToFolderId(id),
    M.FolderIds(
        T.FolderId(Id=folder.id)
    )
  )
  return root


def update_property_node(node_to_insert, field_uri):
  """ Helper function - generates a SetItemField which tells Exchange you want to overwrite the contents of a field."""
  root = T.SetItemField(
            T.FieldURI(FieldURI=field_uri),
            T.CalendarItem(node_to_insert)
        )
  return root


def update_item(event, updated_attributes, calendar_item_update_operation_type):
  """ Saves updates to an event in the store. Only request changes for attributes that have actually changed."""

  root = M.UpdateItem(
    M.ItemChanges(
      T.ItemChange(
        T.ItemId(Id=event.id, ChangeKey=event.change_key),
        T.Updates()
      )
    ),
    ConflictResolution=u"AlwaysOverwrite",
    MessageDisposition=u"SendAndSaveCopy",
    SendMeetingInvitationsOrCancellations=calendar_item_update_operation_type
  )

  update_node = root.xpath(u'/m:UpdateItem/m:ItemChanges/t:ItemChange/t:Updates', namespaces=NAMESPACES)[0]

  # if not send_only_to_changed_attendees:
  #   # We want to resend invites, which you do by setting an attribute to the same value it has. Right now, events
  #   # are always scheduled as Busy time, so we just set that again.
  #   update_node.append(
  #     update_property_node(field_uri="calendar:LegacyFreeBusyStatus", node_to_insert=T.LegacyFreeBusyStatus("Busy"))
  #   )

  if u'html_body' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Body", node_to_insert=T.Body(event.html_body, BodyType="HTML"))
    )

  if u'text_body' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Body", node_to_insert=T.Body(event.text_body, BodyType="Text"))
    )

  if u'subject' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Subject", node_to_insert=T.Subject(event.subject))
    )

  if u'start' in updated_attributes:
    start = convert_datetime_to_utc(event.start)

    update_node.append(
      update_property_node(field_uri="calendar:Start", node_to_insert=T.Start(start.strftime(EXCHANGE_DATETIME_FORMAT)))
    )

  if u'end' in updated_attributes:
    end = convert_datetime_to_utc(event.end)

    update_node.append(
      update_property_node(field_uri="calendar:End", node_to_insert=T.End(end.strftime(EXCHANGE_DATETIME_FORMAT)))
    )

  if u'location' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="calendar:Location", node_to_insert=T.Location(event.location))
    )

  if u'attendees' in updated_attributes:

    if event.required_attendees:
      required = resource_node(element=T.RequiredAttendees(), resources=event.required_attendees)

      update_node.append(
        update_property_node(field_uri="calendar:RequiredAttendees", node_to_insert=required)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:RequiredAttendees"))

    if event.optional_attendees:
      optional = resource_node(element=T.OptionalAttendees(), resources=event.optional_attendees)

      update_node.append(
        update_property_node(field_uri="calendar:OptionalAttendees", node_to_insert=optional)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:OptionalAttendees"))

  if u'resources' in updated_attributes:
    if event.resources:
      resources = resource_node(element=T.Resources(), resources=event.resources)

      update_node.append(
        update_property_node(field_uri="calendar:Resources", node_to_insert=resources)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:Resources"))

  if u'reminder_minutes_before_start' in updated_attributes:
    if event.reminder_minutes_before_start:
      update_node.append(
        update_property_node(field_uri="item:ReminderIsSet", node_to_insert=T.ReminderIsSet('true'))
      )
      update_node.append(
        update_property_node(
          field_uri="item:ReminderMinutesBeforeStart",
          node_to_insert=T.ReminderMinutesBeforeStart(str(event.reminder_minutes_before_start))
        )
      )
    else:
      update_node.append(
        update_property_node(field_uri="item:ReminderIsSet", node_to_insert=T.ReminderIsSet('false'))
      )

  if u'is_all_day' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="calendar:IsAllDayEvent", node_to_insert=T.IsAllDayEvent(str(event.is_all_day).lower()))
    )

  for attr in event.RECURRENCE_ATTRIBUTES:
    if attr in updated_attributes:

      recurrence_node = T.Recurrence()

      if event.recurrence == 'daily':
        recurrence_node.append(
          T.DailyRecurrence(
            T.Interval(str(event.recurrence_interval)),
          )
        )
      elif event.recurrence == 'weekly':
        recurrence_node.append(
          T.WeeklyRecurrence(
            T.Interval(str(event.recurrence_interval)),
            T.DaysOfWeek(event.recurrence_days),
          )
        )
      elif event.recurrence == 'monthly':
        recurrence_node.append(
          T.AbsoluteMonthlyRecurrence(
            T.Interval(str(event.recurrence_interval)),
            T.DayOfMonth(str(event.start.day)),
          )
        )
      elif event.recurrence == 'yearly':
        recurrence_node.append(
          T.AbsoluteYearlyRecurrence(
            T.DayOfMonth(str(event.start.day)),
            T.Month(event.start.strftime("%B")),
          )
        )

      recurrence_node.append(
        T.EndDateRecurrence(
          T.StartDate(event.start.strftime(EXCHANGE_DATE_FORMAT)),
          T.EndDate(event.recurrence_end_date.strftime(EXCHANGE_DATE_FORMAT)),
        )
      )

      update_node.append(
        update_property_node(field_uri="calendar:Recurrence", node_to_insert=recurrence_node)
      )

  return root
