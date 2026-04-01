var PENDING_SHEET_NAME = '会议待归档表'
var ARCHIVE_SHEET_NAME = '文音视频档案'

var ARCHIVE_MEETING_ID_FIELD = '会议唯一ID'
var ARCHIVE_SOURCE_TITLE_FIELD = '来源会议标题'
var ARCHIVE_TOPIC_FIELD = '主题'
var ARCHIVE_DATE_FIELD = '日期'
var ARCHIVE_PEOPLE_FIELD = '相关人员'
var ARCHIVE_TYPE_FIELD = '类型'
var ARCHIVE_TAGS_FIELD = '标签'
var ARCHIVE_LINK_FIELD = '链接'
var ARCHIVE_REMARK_FIELD = '备注'

var PENDING_MEETING_ID_FIELD = '会议ID'
var LEGACY_PENDING_MEETING_ID_FIELD = '会议唯一ID'
var PENDING_TITLE_FIELD = '会议标题'
var PENDING_DATE_FIELD = '会议日期'
var PENDING_LINK_FIELD = '会议链接'
var PENDING_CONFIRM_PEOPLE_FIELD = '确认相关人员'
var PENDING_CONFIRM_TOPIC_FIELD = '确认主题'
var PENDING_CONFIRM_TYPE_FIELD = '确认类型'
var PENDING_CONFIRM_TAGS_FIELD = '确认标签'
var PENDING_STATUS_FIELD = '归档状态'
var PENDING_REMARK_FIELD = '备注'

function findSheetByName(name) {
  var sheets = Application.Sheet.GetSheets()
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].name === name) return sheets[i]
  }
  return null
}

function getFieldNames(sheet) {
  var names = {}
  var fields = sheet.fields || []
  for (var i = 0; i < fields.length; i++) {
    names[fields[i].name] = true
  }
  return names
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

var pendingSheet = findSheetByName(PENDING_SHEET_NAME)
if (!pendingSheet) throw new Error('sheet not found: ' + PENDING_SHEET_NAME)

var archiveSheet = findSheetByName(ARCHIVE_SHEET_NAME)
if (!archiveSheet) throw new Error('sheet not found: ' + ARCHIVE_SHEET_NAME)
var archiveFieldNames = getFieldNames(archiveSheet)

var pendingRecords = getAllRecords(pendingSheet.id)
var archiveRecords = getAllRecords(archiveSheet.id)

var archiveIndex = {}
for (var i = 0; i < archiveRecords.length; i++) {
  var archiveMeetingId = (archiveRecords[i].fields || {})[ARCHIVE_MEETING_ID_FIELD]
  if (archiveMeetingId) archiveIndex[String(archiveMeetingId)] = archiveRecords[i].id
}

for (var j = 0; j < pendingRecords.length; j++) {
  var pending = pendingRecords[j]
  var fields = pending.fields || {}

  if (fields[PENDING_STATUS_FIELD] !== '确认归档') continue

  var meetingId = String(fields[PENDING_MEETING_ID_FIELD] || fields[LEGACY_PENDING_MEETING_ID_FIELD] || '')
  if (!meetingId) continue

  if (archiveIndex[meetingId]) {
    var duplicateUpdate = {}
    duplicateUpdate[PENDING_STATUS_FIELD] = '已归档'
    Application.Record.UpdateRecords({
      SheetId: pendingSheet.id,
      Records: [{ id: pending.id, fields: duplicateUpdate }]
    })
    continue
  }

  var topic = fields[PENDING_CONFIRM_TOPIC_FIELD] || ''
  var archiveType = fields[PENDING_CONFIRM_TYPE_FIELD] || '学术讨论'
  var peopleIds = toRecordIdList(fields[PENDING_CONFIRM_PEOPLE_FIELD])

  if (!topic || peopleIds.length === 0) {
    console.log('SKIPPED_PENDING_ID=' + pending.id + ', topic=' + !!topic + ', peopleCount=' + peopleIds.length)
    continue
  }

  var archiveFields = {}
  archiveFields[ARCHIVE_TOPIC_FIELD] = topic
  archiveFields[ARCHIVE_DATE_FIELD] = fields[PENDING_DATE_FIELD]
  archiveFields[ARCHIVE_PEOPLE_FIELD] = buildLinkFieldValue(peopleIds)
  archiveFields[ARCHIVE_TYPE_FIELD] = archiveType
  if (fields[PENDING_CONFIRM_TAGS_FIELD] && fields[PENDING_CONFIRM_TAGS_FIELD].length) {
    archiveFields[ARCHIVE_TAGS_FIELD] = fields[PENDING_CONFIRM_TAGS_FIELD]
  }
  archiveFields[ARCHIVE_LINK_FIELD] = fields[PENDING_LINK_FIELD] || []

  if (archiveFieldNames[ARCHIVE_REMARK_FIELD] && fields[PENDING_REMARK_FIELD]) {
    archiveFields[ARCHIVE_REMARK_FIELD] = fields[PENDING_REMARK_FIELD]
  }
  if (archiveFieldNames[ARCHIVE_MEETING_ID_FIELD]) {
    archiveFields[ARCHIVE_MEETING_ID_FIELD] = meetingId
  }
  if (archiveFieldNames[ARCHIVE_SOURCE_TITLE_FIELD]) {
    archiveFields[ARCHIVE_SOURCE_TITLE_FIELD] = fields[PENDING_TITLE_FIELD] || ''
  }

  var created = Application.Record.CreateRecords({
    SheetId: archiveSheet.id,
    Records: [{ fields: archiveFields }]
  })
  console.log('ARCHIVE_CREATED=' + JSON.stringify(created))

  var pendingUpdate = {}
  pendingUpdate[PENDING_STATUS_FIELD] = '已归档'

  Application.Record.UpdateRecords({
    SheetId: pendingSheet.id,
    Records: [{ id: pending.id, fields: pendingUpdate }]
  })
}

console.log('done')
