<script setup>
import Variable from './Variable.vue'
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'
import {ref, watchPostEffect} from "vue"
import { instance_edit_state,close_instance_edit,save_and_close_instance_edit } from '@/server_com';

const inst_copy = ref(instance_edit_state.value.tempspace);
const processing_time = ref(new Date(inst_copy.value.next_processing_time));
watchPostEffect(()=>inst_copy.value.next_processing_time = processing_time.value.toISOString());
</script>

<style>
.instance_edit{
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
    background-color: rgba(128, 128, 128, 0.5);
}
.instance_edit_content_section{
    margin: 3em;
    overflow: scroll;
    max-height: 90%;
}
.instance_edit_console_log_display {
    background-color: lightgray;
    white-space: pre;
    max-height: 25em;
    overflow: scroll;
}
</style>

<template>
    <div class="instance_edit" @click.self="close_instance_edit">
        <section class="instance_edit_content_section">
            <h1>Instance: {{ inst_copy.uuid }}</h1>
            <button type="button" class="instance_edit_cancel_button" @click="close_instance_edit">Cancel</button>
            <button type="button" class="instance_edit_save_button" @click="save_and_close_instance_edit">Save</button>
            <VueDatePicker v-model="processing_time"></VueDatePicker>
            <div class="instance_edit_workflow_name">{{ inst_copy.workflow_name }}</div>
            <div class="instance_edit_process_name">{{ inst_copy.processing_step[0] }}</div>
            <div class="instance_edit_process_step">{{ inst_copy.processing_step[1] }}</div>
            <div class="instance_edit_console_log_display">{{ inst_copy.console_log }}</div>
            <button type="button" class="instance_edit_console_clear_button" @click="inst_copy.console_log=''">Clear</button>
            <div class="instance_details_variables">
                <Variable v-for="v in Object.keys(inst_copy.variables)" :key="v" :name="v" :variable="inst_copy.variables[v]" />
            </div>
        </section>
    </div>
</template>