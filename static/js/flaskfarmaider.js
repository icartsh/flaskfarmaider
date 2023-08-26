var SCH_FORM_LINE = '<hr class="">'
var SCH_FORM_TASK = build_sch_form_select('sch-task', '작업', TASK_OPTS, 9, '일정으로 등록할 작업');
var SCH_FORM_DESC = build_sch_form_text('sch-description', '설명', '', 9, '일정 목록에 표시될 제목');
var SCH_FORM_GROUP_TASK = build_sch_form_group('sch-form-group-task', [SCH_FORM_TASK, SCH_FORM_DESC, SCH_FORM_LINE]);
var SCH_FORM_PATH = build_sch_form_text('sch-target-path', '로컬 경로', '', 9, '새로고침/스캔 할 경로<br>Flaskfarm에서 접근 가능한 로컬 경로');
var SCH_FORM_GROUP_PATH = build_sch_form_group('sch-form-group-path', [SCH_FORM_PATH, SCH_FORM_LINE]);
var SCH_FORM_VFS = build_sch_form_text('sch-vfs', 'VFS 리모트', '', 5, 'rclone rc로 접근 가능한 리모트 이름<br>ex. gds:');
var SCH_FORM_RECURSIVE = build_sch_form_checkbox('sch-recursive', 'recursive', 'off', 9, 'rclone refresh의 --recursive 옵션 적용 여부');
var SCH_FORM_GROUP_RCLONE = build_sch_form_group('sch-form-group-rclone', [SCH_FORM_VFS, SCH_FORM_RECURSIVE, SCH_FORM_LINE]);
var SCH_FORM_SCAN_TYPE = build_sch_form_radio('sch-scan-mode', '스캔 방식', SCAN_OPTS, 9, '');
var SCH_FORM_SCAN_PERIODIC = build_sch_form_select('sch-scan-mode-periodic-id', '주기적 스캔 작업', [], 9, 'Plexmate 플러그인의 주기적 스캔 작업 목록')
var SCH_FORM_GROUP_SCAN = build_sch_form_group('sch-form-group-scan', [SCH_FORM_SCAN_TYPE, SCH_FORM_SCAN_PERIODIC, SCH_FORM_LINE]);
var SCH_FORM_CLEAR_TYPE = build_sch_form_radio('sch-clear-type', '파일 정리 유형', CLEAR_OPTS, 9, '파일 정리할 라이브러리의 유형')
var SCH_FORM_CLEAR_LEVEL = build_sch_form_select('sch-clear-level', '파일 정리 단계', [], 3, 'Plexmate 파일 정리 단계')
var SCH_FORM_CLEAR_SECTION = build_sch_form_select('sch-clear-section', '파일 정리 섹션', [], 5, '파일 정리할 라이브러리 섹션')
var SCH_FORM_GROUP_CLEAR = build_sch_form_group('sch-form-group-clear', [SCH_FORM_CLEAR_TYPE, SCH_FORM_CLEAR_LEVEL, SCH_FORM_CLEAR_SECTION, SCH_FORM_LINE]);
var SCH_FORM_SCH_MODE = build_sch_form_radio('sch-schedule-mode', '일정 방식', SCHEDULE_OPTS, 9, '')
var SCH_FORM_SCH_INTERVAL = build_sch_form_text('sch-schedule-interval', '시간 간격', '', 5, 'Interval(minute 단위) 혹은 Cron 설정');
var SCH_FORM_SCH_AUTO = build_sch_form_checkbox('sch-schedule-auto-start', '시작시 일정 등록', 'off', 9, '');
var SCH_FORM_GROUP_SCH = build_sch_form_group('sch-form-group-sch', [SCH_FORM_SCH_MODE, SCH_FORM_SCH_INTERVAL, SCH_FORM_SCH_AUTO, SCH_FORM_LINE]);

function init_schedule() {
    E_SCH_SETTING = $('#sch-setting');
    E_SCH_SETTING.append(SCH_FORM_GROUP_TASK);
    E_TASK = $('#sch-task');
    // 일정 업무 선택에 따라 inputs (비)활성화
    E_TASK.change(function() {
        set_form_by_task($(this).prop('value'));
    });
    E_DESC = $('#sch-description');
    E_GROUP_TASK = $('#sch-form-group-task');
    E_SCH_SETTING.append(SCH_FORM_GROUP_PATH);
    E_PATH = $('#sch-target-path');
    E_GROUP_PATH = $('#sch-form-group-path');
    E_SCH_SETTING.append(SCH_FORM_GROUP_RCLONE);
    E_VFS = $('#sch-vfs');
    E_RECUR = $('#sch-recursive');
    E_GROUP_RCLONE = $('#sch-form-group-rclone');
    E_SCH_SETTING.append(SCH_FORM_GROUP_SCAN);
    E_SCAN_RADIO_0 = $('#sch-scan-mode0');
    E_SCAN_RADIO_1 = $('#sch-scan-mode1');
    E_SCAN_RADIO_2 = $('#sch-scan-mode2');
    // 스캔 방식에 따라 inputs (비)활성화
    $('input[id^="sch-scan-mode"]:radio').change(function() {
        disabled_by_scan_mode($(this).prop('value'));
    });
    E_SCAN_PERIODIC_ID = $('#sch-scan-mode-periodic-id');
    E_GROUP_SCAN = $('#sch-form-group-scan');
    E_SCH_SETTING.append(SCH_FORM_GROUP_CLEAR);
    E_CLEAR_SECTION = $('#sch-clear-section');
    E_CLEAR_RADIO_0 = $('#sch-clear-type0');
    E_CLEAR_RADIO_1 = $('#sch-clear-type1');
    E_CLEAR_RADIO_2 = $('#sch-clear-type2');
    // 라이브러리 타입에 따라 목록 변경
    $('input[id^="sch-clear-type"]:radio').change(function() {
        set_clear_section($(this).prop('value'));
        set_clear_level($(this).prop('value'));
    })
    E_CLEAR_LEVEL = $('#sch-clear-level');
    E_GROUP_CLEAR = $('#sch-form-group-clear');
    E_SCH_SETTING.append(SCH_FORM_GROUP_SCH);
    E_SCH_RADIO_0 = $('#sch-schedule-mode0');
    E_SCH_RADIO_1 = $('#sch-schedule-mode1');
    E_SCH_RADIO_2 = $('#sch-schedule-mode2');
    // 일정 방식 선택에 따라 inputs (비)활성화
    $('input[id^="sch-schedule-mode"]:radio').change(function() {
        E_SCH_AUTO.bootstrapToggle('off');
        disabled_by_schedule_mode($(this).prop('value'));
    });
    E_SCH_AUTO = $('#sch-schedule-auto-start');
    E_INTERVAL = $('#sch-schedule-interval');
    E_GROUP_SCH = $('#sch-form-group-sch');
    E_SAVE_BTN = $('#sch-save-btn');
    // 일정 저장 버튼
    E_SAVE_BTN.on('click', function() {
        id = $(this).data('id');
        formdata = getFormdata('#sch-setting');
        formdata += '&id=' + id;
        globalSendCommand('save', formdata, null, null, function(result) {
            if (result.success) {
                E_MODAL.modal('hide');
                notify(result.data, 'success');
                globalRequestSearch(1);
            } else {
                notify(result.data, 'warning');
            }
        });
    });
    E_ADD_BTN = $('#sch-add-btn');
    // 일정 추가 버튼
    E_ADD_BTN.on('click', function(e) {
        e.preventDefault();
        schedule_modal('new', '');
    });
    E_MODAL_TITLE = $('#sch-add-modal_title');
    E_MODAL = $('#sch-add-modal')
    E_CONFIRM_TITLE = $('#confirm_title');
    E_CONFIRM_BODY = $('#confirm_body');
    E_CONFIRM_BTN = $('#confirm_button');
    E_CONFIRM_MODAL = $("#confirm_modal");
    E_WORKING_DIR = $('#working-directory');
    E_BROWSER_WD = $('#working-directory');
    // 현재 디렉토리
    E_BROWSER_WD.keypress(function(e) {
        if (e.keyCode && e.keyCode == 13) {
            E_BROWSER_WD_SUBMIT.trigger("click");
            return false;
        }
    });
    E_BROWSER_WD_SUBMIT = $('#working-directory-submit');
    // 브라우저 이동 버튼
    E_BROWSER_WD_SUBMIT.on('click', function(e) {
        dir = E_BROWSER_WD.prop('value');
        browser_command({command: 'list', path: dir});
    });
    E_GLOBAL_SEARCH_BTN = $('#globalSearchSearchBtn');
    E_GLOBAL_SEARCH_KEYWORD = $('#keyword');
    // 검색 inputs
    E_GLOBAL_SEARCH_KEYWORD.keypress(function(e) {
        if (e.keyCode && e.keyCode == 13) {
            E_GLOBAL_SEARCH_BTN.trigger("click");
            return false;
        }
    });
    E_GLOBAL_SEARCH_ORDER = $('#order');
    E_GLOBAL_SEARCH_OPTION1 = $('#option1');
    E_GLOBAL_SEARCH_OPTION2 = $('#option2');
    PERIODICS.forEach(function(item, index) {
        E_SCAN_PERIODIC_ID.append(
            $('<option></option>').prop('value', item.idx).html(item.idx + '. ' + item.name + ' : ' + item.desc)
        );
    });
    // 초기 일정 불러오기
    // f'{order}|{page}|{search}|{option1}|{option2}')
    if (LAST_LIST_OPTIONS.length == 5) {
        E_GLOBAL_SEARCH_ORDER.prop('value', LAST_LIST_OPTIONS[0]);
        E_GLOBAL_SEARCH_KEYWORD.prop('value', LAST_LIST_OPTIONS[2]);
        E_GLOBAL_SEARCH_OPTION1.prop('value', LAST_LIST_OPTIONS[3]);
        E_GLOBAL_SEARCH_OPTION2.prop('value', LAST_LIST_OPTIONS[4]);
        globalRequestSearch(LAST_LIST_OPTIONS[1]);
    } else {
        globalRequestSearch('1');
    }
    // 초기 디렉토리 불러오기
    browser_command({
        command: 'list',
        path: E_BROWSER_WD.prop('value'),
        recursive: false,
        scan_mode: SCAN_MODE_KEYS[0],
    });
}

function init_setting() {
    $("body").on('click', '#btn_test_connection_rclone', function (e) {
        e.preventDefault();
        ret = globalSendCommand(
            'command_test_connection',
            $('#setting_rclone_remote_addr').prop('value').trim(),
            $('#setting_rclone_remote_user').prop('value').trim(),
            $('#setting_rclone_remote_pass').prop('value').trim(),
            callback_test_connection
        );
    });

    function callback_test_connection(result) {
        switch (result.ret) {
            case 'success':
                console.log('Connection success');
                $('#btn_test_connection_rclone').text('접속 성공');
                //$('#btn_test_connection_rclone').attr('disabled', true);
                console.log(result.vfses[0]);
                $("#{{ module_name + '_rclone_remote_vfs' }}").prop('value', result.vfses[0]);
                break;
            case 'failed': arguments
                console.log('Connection failed');
                $('#btn_test_connection_rclone').text('접속 실패');
                break;
            default:
                console.log('Connection returns : ${result.ret}');
        }
    }
}

function confirm_modal(title, content, func) {
    E_CONFIRM_TITLE.html(title);
    E_CONFIRM_BODY.html(content);
    // 클릭 이벤트가 bubble up 되면서 중복 실행됨 e.stopImmediatePropagation(); 로 해결 안 됨.
    E_CONFIRM_BTN.prop('onclick', null).off('click');
    E_CONFIRM_BTN.on('click', function(e){
        func();
    });
    E_CONFIRM_MODAL.modal();
}

function copy_to_clipboard(text) {
    window.navigator.clipboard.writeText(text);
    notify('클립보드에 복사하였습니다.', 'success');
}

function browser_command(cmd) {
    if (cmd.command != 'list') {
        notify('작업을 실행합니다.', 'success');
    }
    globalSendCommand(cmd.command, cmd.path, cmd.recursive, cmd.scan_mode + "|-1", function(result) {
        if (result.success) {
            if (cmd.command == 'list') {
                E_WORKING_DIR.prop('value', cmd.path);
                list_dir(JSON.parse(result.data));
            } else {
                notify(result.data, 'success');
            }
        } else {
            notify(result.data, 'warning');
        }
    });
}

function list_dir(result) {
    $('#brw-list-table thead.dir-parent').html('');
    $('#brw-list-table tbody').html('');
    for (var index in result) {
        if (index == 0) {
            link_classes = 'dir-folder no-context restrict-context';
            name_i_classes = 'fa-folder pr-2';
            result[index].size = '';
            result[index].mtime = '';
        } else if (result[index].is_file) {
            link_classes = 'dir-file restrict-context text-decoration-none font-weight-light';
            name_i_classes = 'fa-file pr-2';
        } else {
            link_classes = 'dir-folder';
            name_i_classes = 'fa-folder pr-2';
        }

        td_name = '<td class="pl-3 w-75"><span href="#" class="dir-name pr-5' + link_classes +'"><i class="fa fa-2 ' + name_i_classes + '" aria-hidden="true"></i>' + result[index].name + '</span></td>';
        td_size = '<td class="text-right">' + result[index].size + '</td>';
        td_mtime = '<td class="text-center">' + result[index].mtime + '</td></tr>';
        tr_group = '<tr role="button" data-path="' + result[index].path + '" class="dir-btn browser-context-menu btn-neutral dir-index-' + index + ' ' + link_classes + '">' + td_name + td_size + td_mtime + '</tr>';
        if (index == 0) {
            $('#brw-list-table thead.dir-parent').append(tr_group);
        } else {
            $('#brw-list-table tbody').append(tr_group);
        }
    }

    $('.dir-btn').on('click', function (e) {
        // except file entries
        if ($(this).hasClass('dir-folder')) {
            path = $(this).data('path');
            cmd = {
                command: 'list',
                path: path,
                recursive: false,
                scan_mode: SCAN_MODE_KEYS[0],
            }
            browser_command(cmd);
        }
    });

    // attach context menu
    $.contextMenu({
        selector: '.browser-context-menu',
        className: 'context-menu',
        autohide: true,
        callback: function(command, opt) {
            path = opt.$trigger.data('path');
            cmd = {
                command: command,
                path: path,
                recursive: opt.inputs['recursive'].$input.prop('checked'),
                scan_mode: opt.inputs['scan_mode'].$input.prop('value'),
            }
            browser_command(cmd);
        },
        events: {
            show: function(opt) {
                // console.log(opt.$trigger.data('path'));
            }
        },
        items: {
            [TASK_KEYS[0]]: {
                name: TASKS[TASK_KEYS[0]].name,
                icon: 'fa-refresh',
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            [TASK_KEYS[1]]: {
                name: TASKS[TASK_KEYS[1]].name,
                icon: 'fa-refresh',
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            [TASK_KEYS[2]]: {
                name: TASKS[TASK_KEYS[2]].name,
                icon: 'fa-search',
                disabled: function(){return $(this).hasClass('no-context');},
            },
            sep1: "---------",
            schedule: {
                name: '일정에 추가',
                icon: 'fa-plus',
                callback: function(key, opt, e) {
                    path = $(this).data('path');
                    schedule_modal('browser', {target: path});
                },
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            clipboard: {
                name: '경로 복사',
                icon: 'fa-clipboard',
                callback: function(key, opt, e) {
                    path = $(this).data('path');
                    copy_to_clipboard(path);
                },
                disabled: function(){return $(this).hasClass('no-context');},
            },
            sep2: "---------",
            recursive: {
                name: 'Recursive',
                type: 'checkbox',
                selected: false,
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            scan_mode: {
                name: '스캔 방식',
                type: 'select',
                options: {
                    [SCAN_MODE_KEYS[2]]: SCAN_MODES[SCAN_MODE_KEYS[2]].name,
                    [SCAN_MODE_KEYS[0]]: SCAN_MODES[SCAN_MODE_KEYS[0]].name,
                },
                selected: SCAN_MODE_KEYS[2],
                disabled: function(){return $(this).hasClass('no-context');},
            },
        },
    });
}

// 일정 리스트
// globalRequestSearch@ff_global1.js 에서 make_list() 호출
function make_list(data) {
    $('#sch-list-table tbody').empty();
    for (model of data){
        col_id = '<td class="text-center">' + model.id + '</td>';
        col_task = '<td class="text-center">' + TASKS[model.task].name + '</td>';
        col_interval = '<td class="text-center">' + model.schedule_interval + '</td>';
        col_title = '<td class="">' + model.desc + '</td>';
        if (model.schedule_mode == 'startup') {
            col_switch = '<td class="text-center">' + FF_SCHEDULES[FF_SCHEDULE_KEYS[1]]['name'] + '</td>';
        } else {
            col_switch = '<td class="text-center"><input id="sch-switch-' + model.id;
            col_switch += '" data-id="' + model.id;
            col_switch += '" data-schedule_mode="' + model.schedule_mode;
            col_switch += '" type="checkbox" ' + ((model.is_include) ? 'checked' : '');
            col_switch += ' data-toggle="toggle" class="sch-switch" /></td>';
        }
        col_status = '<td class="text-center">' + ((model.status == STATUS_KEYS[1]) ? '실행중' : '대기중') + '</td>';
        col_ftime = '<td class="text-center">' + model.ftime + '</td>';

        col_menu = '<td class="text-center"><button type="button" class="btn btn-outline-primary sch-context-menu"';
        col_menu += ' data-id=' + model.id;
        col_menu += ' data-task="' + model.task;
        col_menu += '" data-desc="' + model.desc;
        col_menu += '" data-target="' + model.target;
        col_menu += '" data-vfs="' + model.vfs;
        col_menu += '" data-recursive="' + model.recursive;
        col_menu += '" data-scan_mode="' + model.scan_mode;
        col_menu += '" data-periodic_id="' + model.periodic_id;
        col_menu += '" data-schedule_mode="' + model.schedule_mode;
        col_menu += '" data-schedule_interval="' + model.schedule_interval;
        col_menu += '" data-schedule_auto_start="' + model.schedule_auto_start;
        col_menu += '" data-clear_section="' + (model.clear_section ? model.clear_section : -1);
        col_menu += '" data-clear_level="' + (model.clear_level ? model.clear_level : 'start1');
        col_menu += '" data-clear_type="' + (model.clear_type ? model.clear_type : SECTION_TYPES[0]);

        col_menu += '">메뉴</button></td>';

        row_sub = '<tr><td colspan="8" class="p-0"><div id="collapse-' + model.id;
        row_sub += '" class="collapse hide" aria-labelledby="list-' + model.id;
        row_sub += '" data-parent="#sch-accordion"><textarea class="form-control h-50 bg-dark text-light" rows=10>' + model.journal + '</textarea></div></td></tr>';
        row_group = '<tr id="list-' + model.id + '" class="" role="button" data-toggle="collapse" data-target="#collapse-' + model.id;
        row_group += '" aria-expanded="true" aria-controls="collapse-' + model.id + '">';
        row_group += col_id + col_task + col_interval + col_title + col_switch + col_status + col_ftime + col_menu +'</tr>' + row_sub;
        $('#sch-list-table tbody').append(row_group);
    }

    // is_include 토글 활성화
    $('.sch-switch').bootstrapToggle();
    $('.sch-switch').on('change', function(e) {
        $this = $(this);
        mode = $this.data('schedule_mode');
        if (mode == FF_SCHEDULE_KEYS[0]) {
            if ($this.prop('checked')) {
                notify('활성화 할 수 없는 일정 방식입니다.', 'warning');
                $this.bootstrapToggle('off');
            }
            return
        }
        _id = $this.data('id');
        checked = $this.prop('checked');
        globalSendCommand('schedule', _id, checked, null, function(result) {
            if (result.success) {
                notify(result.data, 'success');
            } else {
                notify(result.data, 'warning');
            }
        });
    });

    $('.sch-switch ~ div.toggle-group').on('click', function(e) {
        // collapse까지 bubble up 되는 것 방지
        e.stopPropagation();
        //e.preventDefault();
        //e.stopImmediatePropagation()
        $(this).prev().bootstrapToggle('toggle');
    })

    // 컨텍스트 메뉴
    $.contextMenu({
        selector: '.sch-context-menu',
        trigger: 'left',
        items: {
            edit: {
                name: '편집',
                icon: 'fa-pencil-square-o',
                disabled: function(){return $(this).hasClass('dir-file');},
                callback: function(key, opt, e) {
                    data = opt.$trigger.data();
                    schedule_modal('edit', data);
                },
            },
            delete: {
                name: '삭제',
                icon: 'fa-trash',
                disabled: function(){return $(this).hasClass('dir-file');},
                callback: function(key, opt, e) {
                    data = opt.$trigger.data();
                    confirm_modal('ID: ' + data.id + ' 일정 삭제', "일정을 삭제할까요?", function() {
                        globalSendCommand("delete", data.id, null, null, function(result) {
                            if (result.success) {
                                globalRequestSearch('1');
                                notify(result.data, 'success');
                            } else {
                                notify(result.data, 'warning');
                            }
                        });
                    });
                }
            },
            execute: {
                name: '지금 실행',
                icon: 'fa-play',
                callback: function(key, opt, e) {
                    data = opt.$trigger.data();
                    confirm_modal('ID: ' + data.id + ' 일정 실행', '일정을 실행할까요?', function() {
                        notify('일정을 실행했습니다.', 'success');
                        globalSendCommand("execute", data.id, null, null, function(result) {
                            globalRequestSearch('1');
                            notify(result.data, 'success');
                        });
                    });
                }
            },
        },
    });
}

function disabled_by_schedule_mode(mode) {
    switch(mode) {
        case FF_SCHEDULE_KEYS[0]:
        case FF_SCHEDULE_KEYS[1]:
            E_INTERVAL.prop('disabled', true);
            E_SCH_AUTO.bootstrapToggle('off');
            E_SCH_AUTO.bootstrapToggle('disable');
            break;
        case FF_SCHEDULE_KEYS[2]:
            E_INTERVAL.prop('disabled', false);
            E_SCH_AUTO.bootstrapToggle('enable');
    }
}

function disabled_by_scan_mode(mode) {
    switch(mode) {
        case SCAN_MODE_KEYS[0]:
        case SCAN_MODE_KEYS[2]:
            E_PATH.prop('disabled', false);
            E_SCAN_PERIODIC_ID.prop('disabled', true);
            break;
        case SCAN_MODE_KEYS[1]:
            E_PATH.prop('disabled', true);
            E_SCAN_PERIODIC_ID.prop('disabled', false);
            break;
    }
}

function set_clear_section(type) {
    E_CLEAR_SECTION.empty();
    if (SECTIONS[type]) {
        SECTIONS[type].forEach(function(item) {
            E_CLEAR_SECTION.append(
                $('<option></option>').prop('value', item.id).append(item.name)
            )
        });
    } else {
        console.error('type: ' + type);
        console.error(SECTIONS);
        notify('라이브러리 섹션 정보가 없습니다.', 'warning');
    }
}

function set_clear_level(type) {
    E_CLEAR_LEVEL.empty();
    E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start1').html('1단계'));
    switch(type) {
        case SECTION_TYPES[0]:
        case SECTION_TYPES[1]:
            if (type == SECTION_TYPES[1]) {
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start21').html('2-1단계'));
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start22').html('2-2단계'));
            } else {
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start2').html('2단계'));
            }
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start3').html('3단계'));
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start4').html('4단계'));
            break;
        case SECTION_TYPES[2]:
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start2').html('2단계'));
            break;
    }
}

function schedule_modal(from, data) {
    if (from == 'edit') {
        // 편집
        set_form_by_task(data.task);
        E_SAVE_BTN.data('id', data.id);
        E_TASK.prop('value', data.task);
        E_DESC.prop('value', data.desc);
        E_PATH.prop('value', data.target);
        E_VFS.prop('value', data.vfs);
        E_RECUR.bootstrapToggle((data.recursive) ? 'on' : 'off');
        $('input[id^="sch-scan-mode"]:radio[value="' + data.scan_mode + '"]').prop('checked', true);
        disabled_by_scan_mode(data.scan_mode);
        E_SCAN_PERIODIC_ID.prop('value', data.periodic_id);
        $('input[id^="sch-schedule-mode"]:radio[value="' + data.schedule_mode + '"]').prop('checked', true);
        disabled_by_schedule_mode(data.schedule_mode);
        E_INTERVAL.prop('value', data.schedule_interval);
        E_SCH_AUTO.bootstrapToggle((data.schedule_auto_start) ? 'on' : 'off');
        E_MODAL_TITLE.html('일정 편집 - ' + data.id);
        $('input[id^="sch-clear-type"]:radio[value="' + data.clear_type + '"]').prop('checked', true);
        set_clear_level(data.clear_type);
        set_clear_section(data.clear_type);
        E_CLEAR_SECTION.prop('value', data.clear_section);
        E_CLEAR_LEVEL.prop('value', data.clear_level);
    } else {
        // 새로 추가
        set_form_by_task(TASK_KEYS[0]);
        E_TASK.prop('value', TASK_KEYS[0]);
        E_SAVE_BTN.data('id', -1);
        E_DESC.prop('value', '');
        if (from == 'browser') {
            // 브라우저에서 추가
            E_PATH.prop('value', data.target);
        } else {
            E_PATH.prop('value', '');
        }
        E_VFS.prop('value', VFS);
        E_RECUR.bootstrapToggle('off');
        E_SCAN_RADIO_0.prop('checked', true);
        E_SCAN_PERIODIC_ID.prop('value', 1);
        E_SCH_RADIO_0.prop('checked', true);
        E_INTERVAL.prop('value', '');
        E_SCH_AUTO.bootstrapToggle('off');
        E_CLEAR_RADIO_0.prop('checked', true);
        disabled_by_schedule_mode(FF_SCHEDULE_KEYS[0]);
        disabled_by_scan_mode(SCAN_MODE_KEYS[0]);
        set_clear_section(E_CLEAR_RADIO_0.prop('value'));
        set_clear_level(E_CLEAR_RADIO_0.prop('value'));
        E_MODAL_TITLE.html("일정 추가");
    }
    E_MODAL.modal({backdrop: 'static', keyboard: false}, 'show');
}

function bulid_sch_form_header(title, col) {
    element = '<div class="row" style="padding-top: 10px; padding-bottom:10px; align-items: center;"><div class="col-sm-3 set-left">';
    element += '<strong>' + title + '</strong></div>';
    element += '<div class="col-sm-9">';
    element += '<div class="input-group col-sm-' + col + '">';
    return element;
}

function build_sch_form_footer(desc) {
    element = '</div><div class="col-sm-9"><em>' + desc + '</em>';
    element += '</div></div></div>';
    return element;
}

function build_sch_form_select(id, title, options, col, desc) {
    element = bulid_sch_form_header(title, col);
    element += '<select id="' + id + '" name="' + id + '" class="form-control form-control-sm">';
    if (options.length > 0) {
        for (idx in options) {
            element += '<option value="' + options[idx].value + '">' + options[idx].name + '</option>';
        }
    }
    element += '</select>';
    element += build_sch_form_footer(desc);
    return element;
}

function build_sch_form_text(id, title, value, col, desc) {
    element = bulid_sch_form_header(title, col);
    element += '<input id="' + id + '" name="' + id + '" type="text" class="form-control form-control-sm" value="' + value + '" />';
    element += build_sch_form_footer(desc);
    return element;
}

function build_sch_form_checkbox(id, title, value, col, desc) {
    element = bulid_sch_form_header(title, col);
    element += '<input id="' + id + '" name="' + id + '" type="checkbox" class="form-control form-control-sm" data-toggle="toggle" />';
    element += build_sch_form_footer(desc);
    return element;
}

function build_sch_form_radio(id, title, options, col, desc) {
    element = bulid_sch_form_header(title, col);
    for (idx in options) {
        element += '<div class="custom-control custom-radio custom-control-inline">';
        element += '<input id="'+ id + idx + '" type="radio" class="custom-control-input" name="' + id + '" value="' + options[idx].value +'">';
        element += '<label class="custom-control-label" for="' + id + idx + '">' + options[idx].name + '</label></div>';
    }
    element += build_sch_form_footer(desc);
    return element;
}

function build_sch_form_group(id, elements) {
    element = '<div id="' + id + '">';
    for (idx in elements) {
        element += elements[idx];
    }
    element += '</div';
    return element
}

function set_form_by_task(task) {
    E_GROUP_PATH.detach();
    E_GROUP_RCLONE.detach();
    E_GROUP_SCAN.detach();
    E_GROUP_CLEAR.detach();
    E_GROUP_SCH.detach();
    E_SCH_RADIO_0.prop('disabled', false);
    E_SCH_RADIO_2.prop('disabled', false);
    switch(task){
        case TASK_KEYS[0]:
            E_SCH_SETTING.append(E_GROUP_PATH);
            E_SCH_SETTING.append(E_GROUP_RCLONE);
            E_SCH_SETTING.append(E_GROUP_SCAN);
            E_SCH_SETTING.append(E_GROUP_SCH);
            break;
        case TASK_KEYS[1]:
            E_SCH_SETTING.append(E_GROUP_PATH);
            E_SCH_SETTING.append(E_GROUP_RCLONE);
            E_SCH_SETTING.append(E_GROUP_SCH);
            break;
        case TASK_KEYS[2]:
            E_SCH_SETTING.append(E_GROUP_PATH);
            E_SCH_SETTING.append(E_GROUP_SCAN);
            E_SCH_SETTING.append(E_GROUP_SCH);
            break;
        case TASK_KEYS[3]:
            E_SCH_SETTING.append(E_GROUP_RCLONE);
            E_SCH_SETTING.append(E_GROUP_SCH);
            break;
        case TASK_KEYS[4]:
            E_SCH_SETTING.append(E_GROUP_CLEAR);
            E_SCH_SETTING.append(E_GROUP_SCH);
            break;
        case TASK_KEYS[5]:
            E_SCH_SETTING.append(E_GROUP_SCH);
            E_SCH_RADIO_1.prop('checked', true);
            disabled_by_schedule_mode(FF_SCHEDULE_KEYS[1]);
            E_SCH_RADIO_0.prop('disabled', true);
            E_SCH_RADIO_2.prop('disabled', true);
            break;
    }
}
