<script setup>
import Variable from './Variable.vue'
import {ref} from "vue"
const props = defineProps({
    instance: Object
})
const show_details = ref(false);
function toggle_details_visibility(){
    show_details.value = !show_details.value;
}
function toggle_processing_state(){
    show_details.value = !show_details.value;
}
</script>

<style>
.instance_details {
    display: inline-block;
    border: solid 0.1em;
    padding: 0.5em;
    margin: 1em;
    border-radius: 0em 0.5em 0.5em;
}

.instance_details_console_log_display {
    background-color: lightgray;
    white-space: pre;
}

.instance_details_process_step,
.instance_details_process_name,
.instance_details_state {
    display: inline-block;
}

.instance_details_section_title {
    margin-top: 0;
    margin-bottom: 0;
    display: inline;
}
</style>

<template>
    <div :id="instance.uuid" class="instance_details">
        <button type="button" class="collapse_button instance_details_section_title" @click="toggle_details_visibility">Instance:</button>
        <button type="button" class="instance_details_state" @click="toggle_processing_state">{{instance.state}}TODO:Toggle</button>
        <div class="instance_details_next_processing_time">{{ instance.next_processing_time }}</div>
        <div>TODO: Status Variable</div>
        <div v-if="show_details">
            <div class="instance_details_workflow_name">{{ instance.workflow_name }}</div>
            <div class="instance_details_process_name">{{ instance.processing_step[0] }}</div>:
            <div class="instance_details_process_step">{{ instance.processing_step[1] }}</div>
            <div class="instance_details_console_log_display">{{ instance.console_log }}</div>
            <div class="instance_details_variables">
                <Variable :name="v" :variable="instance.variables[v]" v-for="v in Object.keys(instance.variables)" :key="v"/>
            </div>
        </div>
    </div>
</template>