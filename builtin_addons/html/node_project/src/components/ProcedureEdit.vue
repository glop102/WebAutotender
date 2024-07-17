<script setup>
import {ref,onMounted} from 'vue'
import CommandEdit from './CommandEdit.vue'
import {available_commands,available_commands_names} from "@/server_com"

const proclist = defineModel();

let dragged_elm = null;
let hover_elm = null;
function dragStart(event) {
    // console.log(event);
    var target = normalize_drag_element(event.target);
    if(!target){return;}

    dragged_elm = target;
    // event.dataTransfer.effectAllowed = "move";
}
function dragEnd(event) {
    // console.log(event);
    dragged_elm.classList.remove("drag_being_dragged");
    if(hover_elm){
        hover_elm.classList.remove("drag_border_above");

        move_proc_to_before_proc(
            parseInt(dragged_elm.attributes.indexnum.value,10),
            parseInt(hover_elm.attributes.indexnum.value,10)
        );
    }
}
function dragEnter(event) {
    // console.log(event);
    var target = normalize_drag_element(event.target);
    if(!target){return;}

    if(!target || target === dragged_elm){
        dragged_elm.classList.remove("drag_being_dragged");
        if(hover_elm){
            hover_elm.classList.remove("drag_border_above");
            hover_elm = null;
        }
    }else if(target !== dragged_elm && target.classList){
        if(hover_elm){
            hover_elm.classList.remove("drag_border_above");
        }
        hover_elm = target;
        target.classList.add("drag_border_above");
        dragged_elm.classList.add("drag_being_dragged");
    }
    // event.target.parentNode.insertBefore(dragged_elm, event.target);
}
function dragLeave(event) {
    // console.log(event);
    // var target = normalize_drag_element(event.target);
    // if(target != dragged_elm && target.classList){
    //     target.classList.remove("drag_border_above");
    // }
}
function normalize_drag_element(target){
    while(target && target !== document && !(target.classList.contains("command_edit_procedit_container")) ){
        target = target.parentNode;
    }
    if(target === document){
        return null;
    }
    return target;
}

function move_proc_to_before_proc(moveidx,beforeidx){
    if(moveidx == beforeidx) return;

    const total = proclist.value;
    const shortened_list = total.toSpliced(moveidx,1); // a copy, not an in-place mutation
    if(moveidx < beforeidx){
        beforeidx -= 1;
    }
    proclist.value = shortened_list.toSpliced(beforeidx,0,total[moveidx]);
}

function add_new_proc_command(){
    proclist.value.push({
        "command_name": available_commands_names.value[0],
        "variables":{}
    });
}
function del_proc_command(idx){
    proclist.value.splice(idx,1);
}
</script>

<style>
.drag_border_above{
    border-top: 0.1em black solid;
}
.drag_being_dragged{
    color: lightgrey;
}
.draghandle{
    cursor: grab;
}

.command_edit_procedit_container{
    margin-top: 0.5em;
}
.command_edit_controls_container{
    display: inline;
    float: left;
}
.command_edit_controls_container button{
    display: block;
}
</style>

<template>
    <div>
        <template v-for="idx in proclist.length">
            <div class="command_edit_procedit_container" :indexnum="idx-1" :ondragstart="dragStart" :ondragend="dragEnd" :ondragenter="dragEnter" :ondragleave="dragLeave">
                <div class="command_edit_controls_container">
                    <button type="button" @click="del_proc_command(idx-1)">x</button>
                    <button type="button" class="draghandle" draggable="true">~</button>
                </div>
                <CommandEdit v-model="proclist[idx-1]" />
            </div>
        </template>
        <button type="button" @click="add_new_proc_command">add</button>
    </div>
</template>