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
    $('#confirm_title').html(title);
    $('#confirm_body').html(content);
    // 클릭 이벤트가 bubble up 되면서 중복 실행됨 e.stopImmediatePropagation(); 로 해결 안 됨.
    $('#confirm_button').prop('onclick', null).off('click');
    $('#confirm_button').on('click', function(e){
        func();
    });
    $("#confirm_modal").modal();
}

function copy_to_clipboard(text) {
    window.navigator.clipboard.writeText(text);
    notify('클립보드에 복사하였습니다.', 'success');
}

function browser_command(cmd) {
    if (cmd.command != 'list') {
        notify('작업을 실행합니다.', 'success');
    }
    globalSendCommand(cmd.command, cmd.path, cmd.recursive, null, function(result) {
        if (result.success) {
            if (cmd.command == 'list') {
                $('#working-directory').prop('value', cmd.path);
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

        td_name = '<td class="pl-3"><span href="#" class="dir-name pr-5 ' + link_classes +'"><i class="fa fa-2 ' + name_i_classes + '" aria-hidden="true"></i>' + result[index].name + '</span></td>';
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
                path: path
            }
            browser_command(cmd);
        }
    });

    // attach context menu
    $.contextMenu({
        selector: '.browser-context-menu',
        className: 'context-title',
        autohide: true,
        callback: function(command, opt) {
            path = opt.$trigger.data('path');
            cmd = {
                command: command,
                path: path,
                recursive: opt.inputs['recursive'].$input.prop('checked')
            }
            browser_command(cmd);
        },
        items: {
            [TASK_KEYS[0]]: {
                name: TASKS[TASK_KEYS[0]].name,
                icon: 'fa-refresh',
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            [TASK_KEYS[5]]: {
                name: TASKS[TASK_KEYS[5]].name,
                icon: 'fa-refresh',
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            [TASK_KEYS[7]]: {
                name: TASKS[TASK_KEYS[7]].name,
                icon: 'fa-refresh',
                disabled: function(){return $(this).hasClass('restrict-context');},
            },
            [TASK_KEYS[3]]: {
                name: TASKS[TASK_KEYS[3]].name,
                icon: 'fa-search',
                disabled: function(){return $(this).hasClass('no-context');},
            },
            [TASK_KEYS[1]]: {
                name: TASKS[TASK_KEYS[1]].name,
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
                disabled: function(){return $(this).hasClass('no-context');},
            },
            clipboard: {
                name: '경로 복사',
                icon: 'fa-clipboard',
                callback: function(key, opt, e) {
                    copy_to_clipboard(path);
                },
                disabled: function(){return $(this).hasClass('no-context');},
            },
            sep2: "---------",
            recursive: {
                name: 'Recursive',
                type: 'checkbox',
                selected: false,
                disabled: function(){return $(this).hasClass('no-context');},
            },
        },
    });
}

function disabled_by_schedule_mode(mode) {
    interval = $('#sch-schedule-interval');
    auto = $('#sch-schedule-auto-start');
    interval.prop('disabled', false);
    auto.bootstrapToggle('enable');
    switch(mode) {
        case FF_SCHEDULE_KEYS[0]:
        case FF_SCHEDULE_KEYS[1]:
            interval.prop('disabled', true);
            auto.bootstrapToggle('disable');
            break;
    }
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
            col_switch = '<td class="text-center">' + FF_SCHEDULES[FF_SCHEDULE_KEYS[1]]['name'] + '</td>'
        } else {
            col_switch = '<td class="text-center"><input id="sch-switch-' + model.id;
            col_switch += '" data-id=' + model.id;
            col_switch += ' type="checkbox" ' + ((model.is_include) ? 'checked' : '');
            col_switch += ' data-toggle="toggle" class="sch-switch" /></td>'
        }
        col_status = '<td class="text-center">' + ((model.status == STATUS_KEYS[1]) ? '실행중' : '대기중') + '</td>';
        col_ftime = '<td class="text-center">' + model.ftime + '</td>';

        col_menu = '<td class="text-center"><button type="button" class="btn btn-outline-primary sch-context-menu"'
        col_menu += ' data-id=' + model.id
        col_menu += ' data-task="' + model.task
        col_menu += '" data-desc="' + model.desc
        col_menu += '" data-target="' + model.target
        col_menu += '" data-vfs="' + model.vfs
        col_menu += '" data-recursive="' + model.recursive
        col_menu += '" data-commands="' + model.commands
        col_menu += '" data-schedule_mode="' + model.schedule_mode
        col_menu += '" data-schedule_interval="' + model.schedule_interval
        col_menu += '" data-schedule_auto_start="' + model.schedule_auto_start
        col_menu += '">메뉴</button></td>'

        row_sub = '<tr><td colspan="8" class="p-0"><div id="collapse-' + model.id
        row_sub += '" class="collapse hide" aria-labelledby="list-' + model.id
        row_sub += '" data-parent="#sch-accordion"><textarea class="form-control h-50 bg-dark text-light" rows=10>' + model.journal + '</textarea></div></td></tr>'
        row_group = '<tr id="list-' + model.id + '" class="" role="button" data-toggle="collapse" data-target="#collapse-' + model.id
        row_group += '" aria-expanded="true" aria-controls="collapse-' + model.id + '">'
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
    target = $('#sch-target-path');
    vfs = $('#sch-vfs');
    recur = $('#sch-recursive');
    radio_0 = $('#sch-schedule-mode0');
    radio_1 = $('#sch-schedule-mode1');
    radio_2 = $('#sch-schedule-mode2');
    auto = $('#sch-schedule-auto-start');
    interval = $('#sch-schedule-interval');

    target.prop('disabled', false);
    vfs.prop('disabled', false);
    recur.prop('disabled', false);
    radio_0.prop('disabled', false);
    radio_2.prop('disabled', false);
    interval.prop('disabled', false);
    recur.bootstrapToggle('enable')
    auto.bootstrapToggle('enable');

    switch(task) {
        case TASK_KEYS[2]:
            target.prop('disabled', true);
            vfs.prop('disabled', true);
            recur.bootstrapToggle('disable')
            auto.bootstrapToggle('disable');
            radio_1.prop('checked', true);
            radio_0.prop('disabled', true);
            radio_2.prop('disabled', true);
            interval.prop('disabled', true);
            break;
        case TASK_KEYS[1]:
        case TASK_KEYS[3]:
            vfs.prop('disabled', true);
            recur.bootstrapToggle('disable')
            break;
        case TASK_KEYS[4]:
            target.prop('disabled', true);
            break;
    }
}

function schedule_modal(from, data) {
    save_btn = $('#sch-save-btn');
    task = $('#sch-task');
    desc = $('#sch-description');
    target = $('#sch-target-path');
    vfs = $('#sch-vfs');
    recur = $('#sch-recursive');
    interval = $('#sch-schedule-interval');
    auto = $('#sch-schedule-auto-start');
    title = $('#sch-add-modal_title');
    modal = $('#sch-add-modal')
    if (from == 'edit') {
        // 편집
        save_btn.data('id', data.id);
        task.prop('value', data.task);
        disabled_by_task(data.task);
        desc.prop('value', data.desc);
        target.prop('value', data.target);
        vfs.prop('value', data.vfs);
        recur.bootstrapToggle((data.recursive) ? 'on' : 'off');
        $('input:radio[name="sch-schedule-mode"][value="' + data.schedule_mode + '"]').prop('checked', true);
        disabled_by_schedule_mode(data.schedule_mode)
        interval.prop('value', data.schedule_interval);
        auto.bootstrapToggle((data.schedule_auto_start) ? 'on' : 'off');
        title.html('일정 편집 - ' + data.id);
    } else {
        // 새로 추가
        task.prop('value', TASK_KEYS[0]);
        save_btn.data('id', -1);
        desc.prop('value', '');
        if (from == 'browser') {
            // 브라우저에서 추가
            target.prop('value', data.target);
        } else {
            target.prop('value', '');
        }
        vfs.prop('value', VFS);
        recur.bootstrapToggle('off');
        $('#sch-schedule-mode0').prop('checked', true);
        interval.prop('value', '');
        auto.bootstrapToggle('off');
        title.html("일정 추가");
        disabled_by_task(task.prop('value'));
        disabled_by_schedule_mode(FF_SCHEDULE_KEYS[0]);
    }
    modal.modal({backdrop: 'static', keyboard: false}, 'show');
}
