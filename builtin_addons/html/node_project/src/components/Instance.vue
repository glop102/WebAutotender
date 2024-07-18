<script setup>
import Variable from './Variable.vue'
import {ref} from "vue"
import { toggle_instance_pause,show_instance_edit,delete_instance } from '@/server_com';
const props = defineProps({
    instance: Object
})
const show_details = ref(false);
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
    max-height: 25em;
    overflow: scroll;
}

.instance_details_state {
    display: inline-block;
}

</style>

<template>
    <div class="instance_details">
        <button type="button" @click="show_details = !show_details">Instance:</button>
        <button type="button" @click="toggle_instance_pause(instance.uuid)">{{instance.state}}</button>
        <div v-if="show_details">
            <button type="button" @click="show_instance_edit(instance.uuid)">Edit</button>
            <button type="button" @click="delete_instance(instance.uuid)">Delete</button>
            <div>UUID: {{ instance.workflow_uuid }}</div>
        </div>
        <div class="instance_details_next_processing_time">{{ instance.next_processing_time }}</div>
        <div v-if="instance.variables['status']">{{ instance.variables['status'].value }}</div>
        <div v-if="show_details">
            <div>{{ instance.processing_step[0] }} : {{ instance.processing_step[1] }}</div>
            <div class="instance_details_console_log_display">{{ instance.console_log }}</div>
            <div>
                <Variable v-for="v in Object.keys(instance.variables)" :key="v" :name="v" :variable="instance.variables[v]" />
            </div>
        </div>
    </div>
</template>