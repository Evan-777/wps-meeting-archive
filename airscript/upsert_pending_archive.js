var PEOPLE_SHEET_NAME = '人员'
var PENDING_SHEET_NAME = '会议待归档表'

var PEOPLE_NAME_FIELD = '姓名'
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
var DEFAULT_TAGS = ['方案设计']

var DEFAULT_STATUS = '待确认'

function findSheetByName(name) {
  var sheets = Application.Sheet.GetSheets()
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].name === name) return sheets[i]
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

function resolvePeopleRecordIds(peopleSheet, names) {
  var wanted = {}
  for (var i = 0; i < (names || []).length; i++) {
    wanted[names[i]] = true
  }

  var result = []
  var records = getAllRecords(peopleSheet.id)
  for (var j = 0; j < records.length; j++) {
    var rec = records[j]
    var nameValue = rec.fields && rec.fields[PEOPLE_NAME_FIELD]
    if (wanted[nameValue]) {
      result.push(rec.id)
    }
  }
  return result
}

function buildLinkFieldValue(recordIds) {
  if (!recordIds || recordIds.length === 0) return { recordIds: [] }
  return { recordIds: recordIds }
}

function hasLinkValue(value) {
  if (!value) return false
  if (value.recordIds && value.recordIds.length && value.recordIds.length > 0) return true
  if (value.length && value.length > 0) return true
  return false
}

function normalizeTags(tags) {
  var result = []
  var seen = {}
  for (var i = 0; i < (tags || []).length; i++) {
    var value = String(tags[i] || '').trim()
    if (!value || seen[value]) continue
    seen[value] = true
    result.push(value)
  }
  return result
}

function hasMultipleSelectValue(value) {
  return value && value.length && value.length > 0
}

var argv = (Context && Context.argv) || {}
var missingArgs = []
if (!argv.meetingId) missingArgs.push('meetingId')
if (!argv.meetingTitle) missingArgs.push('meetingTitle')
if (!argv.meetingDate) missingArgs.push('meetingDate')
if (!argv.meetingLink) missingArgs.push('meetingLink')

if (missingArgs.length > 0) {
  console.log('MISSING_ARGS=' + missingArgs.join(','))
  console.log('HINT=upsert_pending_archive should be called by webhook/CLI with Context.argv')
  console.log('done')
} else {

var peopleSheet = findSheetByName(PEOPLE_SHEET_NAME)
if (!peopleSheet) throw new Error('sheet not found: ' + PEOPLE_SHEET_NAME)

var pendingSheet = findSheetByName(PENDING_SHEET_NAME)
if (!pendingSheet) throw new Error('sheet not found: ' + PENDING_SHEET_NAME)

var confirmPeopleIds = resolvePeopleRecordIds(peopleSheet, argv.suggestedPeopleNames || [])
var suggestedTags = normalizeTags(argv.suggestedTags || DEFAULT_TAGS)
var pendingRecords = getAllRecords(pendingSheet.id)
var existing = null

for (var i = 0; i < pendingRecords.length; i++) {
  var record = pendingRecords[i]
  var fields = record.fields || {}
  var currentMeetingId = fields[PENDING_MEETING_ID_FIELD] || fields[LEGACY_PENDING_MEETING_ID_FIELD]
  if (String(currentMeetingId) === String(argv.meetingId)) {
    existing = record
    break
  }
}

var payloadFields = {}
payloadFields[PENDING_MEETING_ID_FIELD] = String(argv.meetingId)
payloadFields[PENDING_TITLE_FIELD] = argv.meetingTitle
payloadFields[PENDING_DATE_FIELD] = argv.meetingDate
payloadFields[PENDING_LINK_FIELD] = [
  {
    address: argv.meetingLink,
    displayText: argv.meetingLink
  }
]
payloadFields[PENDING_CONFIRM_TOPIC_FIELD] = argv.suggestedTopic || ''
payloadFields[PENDING_CONFIRM_TYPE_FIELD] = argv.suggestedType || '学术讨论'

if (!existing) {
  payloadFields[PENDING_CONFIRM_PEOPLE_FIELD] = buildLinkFieldValue(confirmPeopleIds)
  payloadFields[PENDING_CONFIRM_TAGS_FIELD] = suggestedTags.length > 0 ? suggestedTags : DEFAULT_TAGS
  payloadFields[PENDING_STATUS_FIELD] = DEFAULT_STATUS
  payloadFields[PENDING_REMARK_FIELD] = argv.remark || ''

  var created = Application.Record.CreateRecords({
    SheetId: pendingSheet.id,
    Records: [{ fields: payloadFields }]
  })
  console.log('CREATED=' + JSON.stringify(created))
} else {
  var existingStatus = (existing.fields || {})[PENDING_STATUS_FIELD]
  if (existingStatus === '已归档' || existingStatus === '忽略' || existingStatus === '确认归档') {
    console.log('SKIPPED_STATUS=' + existingStatus)
  } else {
    var existingPeople = (existing.fields || {})[PENDING_CONFIRM_PEOPLE_FIELD]
    var existingTags = (existing.fields || {})[PENDING_CONFIRM_TAGS_FIELD]
    if (!hasLinkValue(existingPeople) && confirmPeopleIds.length > 0) {
      payloadFields[PENDING_CONFIRM_PEOPLE_FIELD] = buildLinkFieldValue(confirmPeopleIds)
    }
    if (!hasMultipleSelectValue(existingTags) || (existingTags.length === 1 && existingTags[0] === '方案设计')) {
      payloadFields[PENDING_CONFIRM_TAGS_FIELD] = suggestedTags.length > 0 ? suggestedTags : DEFAULT_TAGS
    }
    if (argv.remark !== undefined && argv.remark !== null && argv.remark !== '') {
      payloadFields[PENDING_REMARK_FIELD] = argv.remark
    }

    var updated = Application.Record.UpdateRecords({
      SheetId: pendingSheet.id,
      Records: [{ id: existing.id, fields: payloadFields }]
    })
    console.log('UPDATED=' + JSON.stringify(updated))
  }
}

console.log('done')
}
