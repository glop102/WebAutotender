<script setup>
import VariableEdit from './VariableEdit.vue'
import {ref,computed} from "vue"
import { close_workflow_edit,save_and_close_workflow_edit,workflow_edit_state } from '@/server_com';

const workflow = ref(workflow_edit_state.value.tempspace);


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
</style>

<template>
    <!-- TODO Have the workflow edit only close when it was successful in pushing state. Otherwise have it sit around disabled or something. -->
    <!-- TODO Have some warning headers in red at the top of the workflow to alert when the server has changed it. -->

    <div class="workflow_edit" @click.self="close_workflow_edit">
        <section class="workflow_edit_content_section">
            <h1>{{ workflow.name }}</h1>
            <button type="button" @click="close_workflow_edit">Cancel</button>
            <button type="button" @click="save_and_close_workflow_edit">Save</button>
            <h2>Constants</h2>
            <div class="workflow_edit_variables">
                <VariableEdit v-for="v in Object.keys(workflow.constants)" :key="v" v-model="workflow.constants[v]" @requested_deletion="delete_constant_variable(v)">{{ v }}</VariableEdit>
                <label>Add Variable</label>
                <input type="text" placeholder="Variable Name" v-model="new_consant_var_name"/>
                <button type="button" @click="add_new_constant_variable">Add</button>
            </div>
            <h2>Setup Variables</h2>
            <div class="workflow_edit_variables">
                <VariableEdit v-for="v in Object.keys(workflow.setup_variables)" :key="v" v-model="workflow.setup_variables[v]" @requested_deletion="delete_constant_variable(v)">{{ v }}</VariableEdit>
            </div>
            <label>Add Variable</label>
            <input type="text" placeholder="Variable Name" v-model="new_consant_var_name"/>
            <button type="button" @click="add_new_constant_variable">Add</button>
            <h2>Procedures</h2>
        </section>
    </div>
</template>