var PENDING_SHEET_NAME = '会议待归档表'
var PEOPLE_SHEET_ID = 3
var PEOPLE_NAME_FIELD_ID = 'R'
var STATUS_OPTIONS = ['待确认', '确认归档', '已归档', '忽略']
var TYPE_OPTIONS = ['学术讨论', '经验分享', '会议讲座', '其他']

var FIELD_MEETING_ID = '会议ID'
var FIELD_TITLE = '会议标题'
var FIELD_DATE = '会议日期'
var FIELD_LINK = '会议链接'
var FIELD_CONFIRM_PEOPLE = '确认相关人员'
var FIELD_CONFIRM_TOPIC = '确认主题'
var FIELD_CONFIRM_TYPE = '确认类型'
var FIELD_CONFIRM_TAGS = '确认标签'
var FIELD_STATUS = '归档状态'
var FIELD_REMARK = '备注'
var ARCHIVE_SHEET_NAME = '文音视频档案'
var ARCHIVE_TAGS_FIELD = '标签'
var DEFAULT_TAGS = ['方案设计']

var LEGACY_FIELD_MEETING_ID = '会议唯一ID'
var LEGACY_FIELD_SUGGESTED_PEOPLE = '建议相关人员'
var LEGACY_FIELD_SUGGESTED_TOPIC = '建议主题'
var LEGACY_FIELD_SUGGESTED_TYPE = '建议类型'
var LEGACY_FIELD_TEACHER_PEOPLE = '老师确认相关人员'
var LEGACY_FIELD_TEACHER_TOPIC = '老师确认主题'
var LEGACY_FIELD_TEACHER_TYPE = '老师确认类型'
var LEGACY_FIELD_MEETING_CREATED_AT = '来源会议创建时间'
var LEGACY_FIELD_MINUTES_GENERATED_AT = '来源纪要生成时间'

var EXPECTED_FIELDS = [
  { name: FIELD_MEETING_ID, type: 'MultiLineText' },
  { name: FIELD_TITLE, type: 'MultiLineText' },
  { name: FIELD_DATE, type: 'Date' },
  { name: FIELD_LINK, type: 'Url' },
  { name: FIELD_CONFIRM_PEOPLE, type: 'Link', linkSheet: PEOPLE_SHEET_ID, linkField: PEOPLE_NAME_FIELD_ID, multipleLinks: true },
  { name: FIELD_CONFIRM_TOPIC, type: 'MultiLineText' },
  { name: FIELD_CONFIRM_TYPE, type: 'SingleSelect', items: TYPE_OPTIONS },
  { name: FIELD_CONFIRM_TAGS, type: 'MultipleSelect', items: [] },
  { name: FIELD_STATUS, type: 'SingleSelect', items: STATUS_OPTIONS },
  { name: FIELD_REMARK, type: 'MultiLineText' }
]

function findSheetByName(name) {
  var sheets = Application.Sheet.GetSheets()
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].name === name) return sheets[i]
  }
  return null
}

function getExistingFields(sheetId) {
  return Application.Field.GetFields({ SheetId: sheetId }) || []
}

function findFieldByName(fields, name) {
  for (var i = 0; i < (fields || []).length; i++) {
    if (fields[i].name === name) return fields[i]
  }
  return null
}

function getAllRecords(sheetId) {
  var all = []
  var offset = null

  while (true) {
    var params = {
      SheetId: sheetId,
      PageSize: 100
    }
    if (offset) params.Offset = offset

    var resp = Application.Record.GetRecords(params)
    var records = resp.records || []
    all = all.concat(records)

    if (!resp.offset) break
    offset = resp.offset
  }

  return all
}

function buildExpectedNameMap() {
  var result = {}
  for (var i = 0; i < EXPECTED_FIELDS.length; i++) {
    result[EXPECTED_FIELDS[i].name] = true
  }
  return result
}

function buildCreateFieldPayload(definition) {
  var payload = {
    name: definition.name,
    type: definition.type
  }

  if (definition.type === 'SingleSelect') {
    var items = []
    for (var i = 0; i < (definition.items || []).length; i++) {
      items.push({ value: definition.items[i] })
    }
    payload.items = items
  }

  if (definition.type === 'MultipleSelect') {
    var multiItems = []
    for (var j = 0; j < (definition.items || []).length; j++) {
      multiItems.push({ value: definition.items[j] })
    }
    payload.items = multiItems
  }

  if (definition.type === 'Link') {
    payload.linkSheet = definition.linkSheet
    payload.linkField = definition.linkField
    payload.multipleLinks = !!definition.multipleLinks
  }

  return payload
}

function createMissingFields(sheetId, existingFields) {
  var existingByName = {}
  var missing = []

  for (var i = 0; i < existingFields.length; i++) {
    if (!existingByName[existingFields[i].name]) {
      existingByName[existingFields[i].name] = true
    }
  }

  for (var j = 0; j < EXPECTED_FIELDS.length; j++) {
    var definition = EXPECTED_FIELDS[j]
    if (existingByName[definition.name]) {
      console.log('EXISTS=' + definition.name)
      continue
    }
    missing.push(buildCreateFieldPayload(definition))
  }

  if (missing.length === 0) {
    console.log('NO_MISSING_FIELDS')
    return
  }

  var created = Application.Field.CreateFields({
    SheetId: sheetId,
    Fields: missing
  })
  console.log('CREATED=' + JSON.stringify(created))
}

function toRecordIdList(value) {
  if (!value) return []
  if (value.recordIds) return value.recordIds
  if (value.length) return value
  return []
}

function buildLinkFieldValue(recordIds) {
  if (!recordIds || recordIds.length === 0) return { recordIds: [] }
  return { recordIds: recordIds }
}

function buildMultipleSelectFieldValue(values) {
  if (!values || values.length === 0) return []
  return values
}

function hasTextValue(value) {
  return value !== undefined && value !== null && String(value) !== ''
}

function hasMultipleSelectValue(value) {
  return value && value.length && value.length > 0
}

function pickTextValue(fields, names) {
  for (var i = 0; i < names.length; i++) {
    var value = fields[names[i]]
    if (hasTextValue(value)) return String(value)
  }
  return ''
}

function pickLinkRecordIds(fields, names) {
  for (var i = 0; i < names.length; i++) {
    var recordIds = toRecordIdList(fields[names[i]])
    if (recordIds.length > 0) return recordIds
  }
  return []
}

function pickMultipleSelectValues(fields, names) {
  for (var i = 0; i < names.length; i++) {
    var value = fields[names[i]]
    if (hasMultipleSelectValue(value)) return value
  }
  return []
}

function getArchiveTagOptions() {
  var archiveSheet = findSheetByName(ARCHIVE_SHEET_NAME)
  if (!archiveSheet) {
    throw new Error('archive sheet not found: ' + ARCHIVE_SHEET_NAME)
  }

  var archiveFields = getExistingFields(archiveSheet.id)
  var tagsField = findFieldByName(archiveFields, ARCHIVE_TAGS_FIELD)
  if (!tagsField) {
    throw new Error('archive field not found: ' + ARCHIVE_TAGS_FIELD)
  }

  var items = tagsField.items || []
  var values = []
  for (var i = 0; i < items.length; i++) {
    if (items[i] && items[i].value) values.push(items[i].value)
  }
  if (values.length === 0) {
    throw new Error('archive field has no selectable items: ' + ARCHIVE_TAGS_FIELD)
  }
  return values
}

function migrateLegacyRecords(sheetId) {
  var records = getAllRecords(sheetId)

  for (var i = 0; i < records.length; i++) {
    var record = records[i]
    var fields = record.fields || {}
    var updateFields = {}

    var meetingId = pickTextValue(fields, [FIELD_MEETING_ID, LEGACY_FIELD_MEETING_ID])
    if (meetingId && String(fields[FIELD_MEETING_ID] || '') !== meetingId) {
      updateFields[FIELD_MEETING_ID] = meetingId
    }

    var confirmPeople = pickLinkRecordIds(fields, [
      FIELD_CONFIRM_PEOPLE,
      LEGACY_FIELD_TEACHER_PEOPLE,
      LEGACY_FIELD_SUGGESTED_PEOPLE
    ])
    if (confirmPeople.length > 0) {
      var currentPeople = toRecordIdList(fields[FIELD_CONFIRM_PEOPLE])
      if (currentPeople.join(',') !== confirmPeople.join(',')) {
        updateFields[FIELD_CONFIRM_PEOPLE] = buildLinkFieldValue(confirmPeople)
      }
    }

    var confirmTopic = pickTextValue(fields, [
      FIELD_CONFIRM_TOPIC,
      LEGACY_FIELD_TEACHER_TOPIC,
      LEGACY_FIELD_SUGGESTED_TOPIC
    ])
    if (confirmTopic && String(fields[FIELD_CONFIRM_TOPIC] || '') !== confirmTopic) {
      updateFields[FIELD_CONFIRM_TOPIC] = confirmTopic
    }

    var confirmType = pickTextValue(fields, [
      FIELD_CONFIRM_TYPE,
      LEGACY_FIELD_TEACHER_TYPE,
      LEGACY_FIELD_SUGGESTED_TYPE
    ])
    if (confirmType && String(fields[FIELD_CONFIRM_TYPE] || '') !== confirmType) {
      updateFields[FIELD_CONFIRM_TYPE] = confirmType
    }

    var confirmTags = pickMultipleSelectValues(fields, [FIELD_CONFIRM_TAGS])
    if (confirmTags.length === 0) {
      updateFields[FIELD_CONFIRM_TAGS] = buildMultipleSelectFieldValue(DEFAULT_TAGS)
    }

    if (Object.keys(updateFields).length === 0) continue

    var updated = Application.Record.UpdateRecords({
      SheetId: sheetId,
      Records: [{ id: record.id, fields: updateFields }]
    })
    console.log('MIGRATED=' + JSON.stringify(updated))
  }
}

function cleanupUnexpectedFields(sheetId, fields) {
  var keepByName = buildExpectedNameMap()
  var seenNames = {}
  var deleteIds = []

  for (var i = 0; i < fields.length; i++) {
    var field = fields[i]

    if (!keepByName[field.name]) {
      console.log('DELETE_EXTRA=' + field.name + ' (' + field.id + ')')
      deleteIds.push(field.id)
      continue
    }

    if (seenNames[field.name]) {
      console.log('DELETE_DUPLICATE=' + field.name + ' (' + field.id + ')')
      deleteIds.push(field.id)
      continue
    }

    seenNames[field.name] = true
  }

  if (deleteIds.length === 0) {
    console.log('NO_EXTRA_FIELDS')
    return
  }

  var deleted = Application.Field.DeleteFields({
    SheetId: sheetId,
    FieldIds: deleteIds
  })
  console.log('DELETED=' + JSON.stringify(deleted))
}

var pendingSheet = findSheetByName(PENDING_SHEET_NAME)
if (!pendingSheet) {
  throw new Error('pending sheet not found: ' + PENDING_SHEET_NAME)
}

EXPECTED_FIELDS[7].items = getArchiveTagOptions()

var existingFields = getExistingFields(pendingSheet.id)
createMissingFields(pendingSheet.id, existingFields)
migrateLegacyRecords(pendingSheet.id)
cleanupUnexpectedFields(pendingSheet.id, getExistingFields(pendingSheet.id))
console.log('done')
