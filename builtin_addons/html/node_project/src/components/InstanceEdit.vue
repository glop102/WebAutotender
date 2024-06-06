<script setup>
import VariableEdit from './VariableEdit.vue'
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
    ()=>
        workflows.value[instance.value.workflow_name] ? 
        Object.keys(workflows.value[instance.value.workflow_name].procedures)
        : [instance.value.processing_step[0]]
);
const available_procedure_steps = computed(
    ()=>
        workflows.value[instance.value.workflow_name] ? // if the workflow exists
            workflows.value[instance.value.workflow_name]
            .procedures[instance.value.processing_step[0]] ? // if a procedure with the current name exists
                workflows.value[instance.value.workflow_name] // give an array of command names in that procedure
                .procedures[instance.value.processing_step[0]]
                .map((proc_step)=>proc_step.command_name)
            : []
        : []
);

const new_var_name = ref("");
function add_new_variable(){
    let var_name = new_var_name.value;
    if(var_name.length == 0){
        return;
    }
    if(Object.keys(instance.value.variables).includes(var_name)){
        return;
    }
    instance.value.variables[var_name] = {
        "value":"",
        "typename":"String"
    };
    new_var_name.value="";
}
function delete_variable(var_name){
    if(!Object.keys(instance.value.variables).includes(var_name)){
        return;
    }
    delete instance.value.variables[var_name];
}
</script>

<style>
.instance_edit{
    width: 100%;
    height: 100%;
    position: fixed;
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
    <!-- TODO Add in the workflow variables to the side for more easily knowing what to reference -->
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
                <option v-if="available_procedure_steps.length==0" :value="instance.processing_step[1]">{{instance.processing_step[1]}} - unknown</option>
                <option v-for="(command_name,idx) in available_procedure_steps" :key="idx" :value="idx">{{idx}} - {{ command_name }}</option>
            </select>
            <div class="instance_edit_console_display" v-if="instance.console_log.length">
                <label>Console Log</label>
                <div class="instance_edit_console_log_display">{{ instance.console_log }}</div>
                <button type="button" class="instance_edit_console_clear_button" @click="instance.console_log=''">Clear</button>
            </div>
            <div class="instance_edit_variables">
                <VariableEdit v-for="v in Object.keys(instance.variables)" :key="v" v-model="instance.variables[v]" @requested_deletion="delete_variable(v)">{{ v }}</VariableEdit>
                <label>Add Variable</label>
                <input type="text" placeholder="Variable Name" v-model="new_var_name"/>
                <button type="button" @click="add_new_variable">Add</button>
            </div>
        </section>
    </div>
</template>