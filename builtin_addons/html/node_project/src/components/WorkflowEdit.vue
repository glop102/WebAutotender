<script setup>
import VariableEdit from './VariableEdit.vue'
import ProcedureEdit from './ProcedureEdit.vue';
import {ref,computed} from "vue"
import { close_workflow_edit,save_and_close_workflow_edit,workflow_edit_state } from '@/server_com';

const workflow = ref(workflow_edit_state.value.tempspace);
const current_procedure = ref("start");

const new_consant_var_name = ref("");
function add_new_constant_variable(){
    let var_name = new_consant_var_name.value;
    if(var_name.length == 0){
        return;
    }
    if(Object.keys(workflow.value.constants).includes(var_name)){
        return;
    }
    workflow.value.constants[var_name] = {
        "value":"",
        "typename":"String"
    };
    new_consant_var_name.value="";
}
function delete_constant_variable(var_name){
    if(!Object.keys(workflow.value.constants).includes(var_name)){
        return;
    }
    delete workflow.value.constants[var_name];
}

const new_setup_var_name = ref("");
function add_new_setup_variable(){
    let var_name = new_setup_var_name.value;
    if(var_name.length == 0){
        return;
    }
    if(Object.keys(workflow.value.setup_variables).includes(var_name)){
        return;
    }
    workflow.value.setup_variables[var_name] = {
        "value":"",
        "typename":"String"
    };
    new_consant_var_name.value="";
}
function delete_setup_variable(var_name){
    if(!Object.keys(workflow.value.setup_variables).includes(var_name)){
        return;
    }
    delete workflow.value.setup_variables[var_name];
}

const new_procedure_name = ref("");
</script>

<style>
.workflow_edit{
    width: 100%;
    height: 100%;
    position: fixed;
    top: 0;
    left: 0;
    background-color: rgba(128, 128, 128, 0.5);
}
.workflow_edit_content_section{
    margin: 3em;
    overflow: scroll;
    max-height: 90%;
}
.workflow_edit_variables {
    margin-top: 1em;
}
label{
    display: block;
}
.workflow_edit_title{
    display: block;
    width: 20em;
    font-size: 1.25em;
}
</style>

<template>
    <!-- TODO Have the workflow edit only close when it was successful in pushing state. Otherwise have it sit around disabled or something. -->
    <!-- TODO Have some warning headers in red at the top of the workflow to alert when the server has changed it. -->

    <div class="workflow_edit" @click.self="close_workflow_edit">
        <section class="workflow_edit_content_section">
            <button type="button" @click="close_workflow_edit">Cancel</button>
            <button type="button" @click="save_and_close_workflow_edit">Save</button>
            <input type="text" v-model="workflow.name" class="workflow_edit_title"/>
            <h3>Constants</h3>
            <div class="workflow_edit_variables">
                <VariableEdit v-for="v in Object.keys(workflow.constants)" :key="v" v-model="workflow.constants[v]" @requested_deletion="delete_constant_variable(v)">{{ v }}</VariableEdit>
                <label>Add Variable</label>
                <input type="text" placeholder="Variable Name" v-model="new_consant_var_name"/>
                <button type="button" @click="add_new_constant_variable">Add</button>
            </div>
            <h3>Setup Variables</h3>
            <div class="workflow_edit_variables">
                <VariableEdit v-for="v in Object.keys(workflow.setup_variables)" :key="v" v-model="workflow.setup_variables[v]" @requested_deletion="delete_setup_variable(v)">{{ v }}</VariableEdit>
            </div>
            <label>Add Variable</label>
            <input type="text" placeholder="Variable Name" v-model="new_setup_var_name"/>
            <button type="button" @click="add_new_setup_variable">Add</button>
            <h3>Procedures</h3>
            <input type="text" placeholder="procedure name" v-model="new_procedure_name"/>
            <button type="button">add</button>
            <br>
            <select v-model="current_procedure">
                <option v-for="procname in Object.keys(workflow.procedures)" :value="procname">{{ procname }}</option>
            </select>
            <button v-if="current_procedure != 'start'" type="button">delete</button>
            <ProcedureEdit v-model="workflow.procedures[current_procedure]" />
        </section>
    </div>
</template>