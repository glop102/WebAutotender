<script setup>
import Variable from './Variable.vue'
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'
import {ref,computed} from "vue"
import { instance_edit_state,close_instance_edit,save_and_close_instance_edit } from '@/server_com';
import { workflow_names,workflows } from '@/server_com';

instance_edit_state.value.tempspace.next_processing_time = instance_edit_state.value.tempspace.next_processing_time.slice(0, 19);
const instance = ref(instance_edit_state.value.tempspace);

//For orphans to have their original workflow name be an option to select because the workflow name otherwise does not exist
const original_workflow_name = workflow_names.value.includes(instance.value.workflow_name) ? undefined : instance.value.workflow_name;

const available_procedure_names = computed(
    ()=>Object.keys(workflows.value[instance.value.workflow_name].procedures)
);
const available_procedure_steps = computed(
    ()=>
        workflows.value[instance.value.workflow_name]
        .procedures[instance.value.processing_step[0]]
        .map((proc_step)=>proc_step.command_name)
);
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
.instance_edit_console_display,
.instance_edit_variables {
    margin-top: 1em;
}
label{
    display: block;
}
</style>

<template>
    <div class="instance_edit" @click.self="close_instance_edit">
        <section class="instance_edit_content_section">
            <h1>Instance: {{ instance.uuid }}</h1>
            <button type="button" class="instance_edit_cancel_button" @click="close_instance_edit">Cancel</button>
            <button type="button" class="instance_edit_save_button" @click="save_and_close_instance_edit">Save</button> -
            <button type="button" class="instance_edit_delete_button" @click="">Delete</button>
            <label>Next Processing Time</label>
            <input type="datetime-local" v-model="instance.next_processing_time" step="1" />
            <label>Associated Workflow</label>
            <select v-model="instance.workflow_name">
                <option v-if="original_workflow_name" :value="original_workflow_name">{{ original_workflow_name }}</option> <!-- For orphans since the workflow they have does not exist -->
                <option v-for="name in workflow_names" :key="name" :value="name">{{ name }}</option>
            </select>
            <label>Processing Step</label>
            <select v-model="instance.processing_step[0]">
                <option v-for="proc_name in available_procedure_names" :key="proc_name" :value="proc_name">{{ proc_name }}</option>
            </select>
            <select v-model="instance.processing_step[1]">
                <option v-for="(command_name,idx) in available_procedure_steps" :key="idx" :value="idx">{{idx}} - {{ command_name }}</option>
            </select>
            <div class="instance_edit_console_display" v-if="instance.console_log.length">
                <label>Console Log</label>
                <div class="instance_edit_console_log_display">{{ instance.console_log }}</div>
                <button type="button" class="instance_edit_console_clear_button" @click="instance.console_log=''">Clear</button>
            </div>
            <div class="instance_edit_variables">
                <!-- Needed items for variables: delete button, name input field, variable type, variable value -->
                <!-- Probably will want a VariableEdit component so we can have some specialized inputs like a color picker -->
                <Variable v-for="v in Object.keys(instance.variables)" :key="v" :name="v" :variable="instance.variables[v]" />
            </div>
        </section>
    </div>
</template>