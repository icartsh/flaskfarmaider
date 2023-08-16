// elements
function set_elements() {
    E_TARGET = $('#sch-target-path');
    E_VFS = $('#sch-vfs');
    E_RECUR = $('#sch-recursive');
    E_SCH_RADIO_0 = $('#sch-schedule-mode0');
    E_SCH_RADIO_1 = $('#sch-schedule-mode1');
    E_SCH_RADIO_2 = $('#sch-schedule-mode2');
    E_SCH_AUTO = $('#sch-schedule-auto-start');
    E_INTERVAL = $('#sch-schedule-interval');
    E_SCAN_RADIO_0 = $('#sch-scan-mode0');
    E_SCAN_RADIO_1 = $('#sch-scan-mode1');
    E_SCAN_RADIO_2 = $('#sch-scan-mode2');
    E_SCAN_PERIODIC_ID = $('#sch-scan-mode-periodic-id');
    E_SAVE_BTN = $('#sch-save-btn');
    E_ADD_BTN = $('#sch-add-btn');
    E_TASK = $('#sch-task');
    E_DESC = $('#sch-description');
    E_MODAL_TITLE = $('#sch-add-modal_title');
    E_MODAL = $('#sch-add-modal')
    E_CONFIRM_TITLE = $('#confirm_title');
    E_CONFIRM_BODY = $('#confirm_body');
    E_CONFIRM_BTN = $('#confirm_button');
    E_CONFIRM_MODAL = $("#confirm_modal");
    E_WORKING_DIR = $('#working-directory');
    E_BROWSER_WD = $('#working-directory');
    E_BROWSER_WD_SUBMIT = $('#working-directory-submit');
    E_GLOBAL_SEARCH_BTN = $('#globalSearchSearchBtn');
    E_GLOBAL_SEARCH_KEYWORD = $('#keyword');
    E_GLOBAL_SEARCH_ORDER = $('#order');
    E_GLOBAL_SEARCH_OPTION1 = $('#option1');
    E_GLOBAL_SEARCH_OPTION2 = $('#option2');
    E_CLEAR_SECTION = $('#sch-clear-section');
    E_CLEAR_TYPE = $('#sch-clear-type');
    E_CLEAR_LEVEL = $('#sch-clear-level');
}

function split_by_newline(text) {
    if (text != null){
        result = text.split("\n").map(function(item) {
            return item.trim();
        });
        return result;
    } else {
        return text;
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

    // except file entries
    $('.dir-btn').on('click', function (e) {
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
    $('#sch-list-table tbody').html('');
    for (model of data){
        col_id = '<td class="text-center">' + model.id + '</td>';
        col_task = '<td class="text-center">' + TASKS[model.task].name + '</td>';
        col_interval = '<td class="text-center">' + model.schedule_interval + '</td>';
        col_title = '<td class="">' + model.desc + '</td>';
        if (model.schedule_mode == 'startup') {
            col_switch = '<td class="text-center">' + FF_SCHEDULES[FF_SCHEDULE_KEYS[1]]['name'] + '</td>';
        } else {
            col_switch = '<td class="text-center"><input id="sch-switch-' + model.id;
            col_switch += '" data-id=' + model.id;
            col_switch += ' type="checkbox" ' + ((model.is_include) ? 'checked' : '');
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
        col_menu += '" data-clear_section="' + model.clear_section;
        col_menu += '" data-clear_level="' + model.clear_level;
        col_menu += '" data-clear_type="' + model.clear_type;
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
        _id = $(this).data('id');
        checked = $(this).prop('checked');
        globalSendCommand('schedule', _id, checked);
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

function disabled_by_task(task) {
    // reset inputs
    E_TARGET.prop('disabled', false);
    E_VFS.prop('disabled', false);
    E_RECUR.bootstrapToggle('enable')
    E_SCH_RADIO_0.prop('disabled', false);
    E_SCH_RADIO_1.prop('disabled', false);
    E_SCH_RADIO_2.prop('disabled', false);
    E_INTERVAL.prop('disabled', false);
    E_SCH_AUTO.bootstrapToggle('enable');
    E_SCAN_RADIO_0.prop('disabled', false);
    E_SCAN_RADIO_1.prop('disabled', false);
    E_SCAN_RADIO_2.prop('disabled', false);
    E_SCAN_PERIODIC_ID.prop('disabled', false);
    disabled_by_schedule_mode($('input[id^="sch-schedule-mode"][type="radio"]:checked').prop('value'));
    disabled_by_scan_mode($('input[id^="sch-scan-mode"][type="radio"]:checked').prop('value'));

    if (task == TASK_KEYS[4]) {
        E_CLEAR_SECTION.prop('disabled', false);
        E_CLEAR_TYPE.prop('disabled', false);
        E_CLEAR_LEVEL.prop('disabled', false);
    } else {
        E_CLEAR_SECTION.prop('disabled', true);
        E_CLEAR_TYPE.prop('disabled', true);
        E_CLEAR_LEVEL.prop('disabled', true);
    }

    switch(task) {
        case TASK_KEYS[4]:
        case TASK_KEYS[5]:
            E_TARGET.prop('disabled', true);
            E_VFS.prop('disabled', true);
            E_RECUR.bootstrapToggle('off');
            E_RECUR.bootstrapToggle('disable');
            if (task == TASK_KEYS[5]) {
                E_SCH_RADIO_0.prop('disabled', true);
                E_SCH_RADIO_2.prop('disabled', true);
                E_SCH_RADIO_1.prop('checked', true);
                E_INTERVAL.prop('disabled', true);
                E_SCH_AUTO.bootstrapToggle('off');
                E_SCH_AUTO.bootstrapToggle('disable');
                disabled_by_schedule_mode($('input[id^="sch-schedule-mode"][type="radio"]:checked').prop('value'));
            }
            E_SCAN_RADIO_0.prop('disabled', true);
            E_SCAN_RADIO_1.prop('disabled', true);
            E_SCAN_RADIO_2.prop('disabled', true);
            E_SCAN_PERIODIC_ID.prop('disabled', true);
            break;
        case TASK_KEYS[1]:
        case TASK_KEYS[3]:
            if (task == TASK_KEYS[3]){
                E_TARGET.prop('disabled', true);
            }
            E_SCAN_RADIO_0.prop('disabled', true);
            E_SCAN_RADIO_1.prop('disabled', true);
            E_SCAN_RADIO_2.prop('disabled', true);
            E_SCAN_PERIODIC_ID.prop('disabled', true);
            break;
        case TASK_KEYS[2]:
            E_VFS.prop('disabled', true);
            E_RECUR.bootstrapToggle('off');
            E_RECUR.bootstrapToggle('disable');
            break;
    }
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
            E_TARGET.prop('disabled', false);
            E_SCAN_PERIODIC_ID.prop('disabled', true);
            break;
        case SCAN_MODE_KEYS[1]:
            E_TARGET.prop('disabled', true);
            E_SCAN_PERIODIC_ID.prop('disabled', false);
            break;
    }
}

function set_clear_section(type) {
    E_CLEAR_SECTION.html('');
    if (['movie', 'show', 'music'].includes(type)) {
        SECTIONS[type].forEach(function(item) {
            E_CLEAR_SECTION.append(
                $('<option></option>').prop('value', item.id).html(item.name)
            )
        });
    } else {
        console.error('type: ' + type);
        console.error(SECTIONS);
    }
}

function set_clear_level(type) {
    E_CLEAR_LEVEL.html('');
    E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start1').html('1단계'));
    switch(type) {
        case 'movie':
        case 'show':
            if (type == 'show') {
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start21').html('2-1단계'));
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start22').html('2-2단계'));
            } else {
                E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start2').html('2단계'));
            }
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start3').html('3단계'));
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start4').html('4단계'));
            break;
        case 'music':
            E_CLEAR_LEVEL.append($('<option></option>').prop('value', 'start2').html('2단계'));
            break;
    }
}

function schedule_modal(from, data) {
    PERIODICS.forEach(function(item, index) {
        E_SCAN_PERIODIC_ID.append(
            $('<option></option>').prop('value', item.idx).html(item.idx + '. ' + item.name + ' : ' + item.desc)
        );
    });

    if (from == 'edit') {
        // 편집
        E_SAVE_BTN.data('id', data.id);
        E_TASK.prop('value', data.task);
        E_DESC.prop('value', data.desc);
        E_TARGET.prop('value', data.target);
        E_VFS.prop('value', data.vfs);
        E_RECUR.bootstrapToggle((data.recursive) ? 'on' : 'off');
        $('input:radio[name="sch-scan-mode"][value="' + data.scan_mode + '"]').prop('checked', true);
        disabled_by_scan_mode(data.scan_mode);
        E_SCAN_PERIODIC_ID.prop('value', data.periodic_id);
        $('input:radio[name="sch-schedule-mode"][value="' + data.schedule_mode + '"]').prop('checked', true);
        disabled_by_schedule_mode(data.schedule_mode);
        E_INTERVAL.prop('value', data.schedule_interval);
        E_SCH_AUTO.bootstrapToggle((data.schedule_auto_start) ? 'on' : 'off');
        E_MODAL_TITLE.html('일정 편집 - ' + data.id);
        E_CLEAR_TYPE.prop('value', data.clear_type);
        set_clear_section(data.clear_type);
        set_clear_level(data.clear_type);
        E_CLEAR_SECTION.prop('value', data.clear_section);
        E_CLEAR_LEVEL.prop('value', data.clear_level);
        disabled_by_task(data.task);
    } else {
        // 새로 추가
        E_TASK.prop('value', TASK_KEYS[0]);
        E_SAVE_BTN.data('id', -1);
        E_DESC.prop('value', '');
        if (from == 'browser') {
            // 브라우저에서 추가
            E_TARGET.prop('value', data.target);
        } else {
            E_TARGET.prop('value', '');
        }
        E_VFS.prop('value', VFS);
        E_RECUR.bootstrapToggle('off');
        E_SCAN_RADIO_0.prop('checked', true);
        E_SCAN_PERIODIC_ID.prop('value', 1);
        E_SCH_RADIO_0.prop('checked', true);
        E_INTERVAL.prop('value', '');
        E_SCH_AUTO.bootstrapToggle('off');
        E_CLEAR_TYPE.prop('value', 'movie');
        disabled_by_task(E_TASK.prop('value'));
        disabled_by_schedule_mode(FF_SCHEDULE_KEYS[0]);
        disabled_by_scan_mode(SCAN_MODE_KEYS[0]);
        set_clear_section(E_CLEAR_TYPE.prop('value'));
        set_clear_level(E_CLEAR_TYPE.prop('value'));
        E_MODAL_TITLE.html("일정 추가");
    }
    E_MODAL.modal({backdrop: 'static', keyboard: false}, 'show');
}
