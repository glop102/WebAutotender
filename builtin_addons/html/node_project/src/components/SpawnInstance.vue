<script setup>
import {ref,computed} from "vue"
import Variable from "./Variable.vue"
import VariableEdit from './VariableEdit.vue'
import {workflows} from "@/server_com.js"
import {close_spawninstance_edit,save_and_close_spawninstance_edit,spawninstance_edit_state} from "@/server_com.js"

const workflow = ref(workflows.value[spawninstance_edit_state.value.workflow_uuid]);
const instance_variables = ref(spawninstance_edit_state.value.tempspace);

const missing_variables = computed(
    () => Object.keys(workflow.value.setup_variables).filter(
        (varname) => !Object.keys(instance_variables.value).includes(varname)
    )
);
const expected_variables = computed(
    () => Object.keys(workflow.value.setup_variables).filter(
        (varname) => Object.keys(instance_variables.value).includes(varname)
    )
);
const extra_variables = computed(
    () => Object.keys(instance_variables.value).filter(
        (varname) => !Object.keys(workflow.value.setup_variables).includes(varname)
    )
);

const new_setup_var_name = ref("");
function add_new_setup_variable(){
    let var_name = new_setup_var_name.value;
    if(var_name.length == 0){
        return;
    }
    if(Object.keys(instance_variables.value).includes(var_name)){
        return;
    }
    instance_variables.value[var_name] = {
        "value":"",
        "typename":"String"
    };
    new_setup_var_name.value="";
}
function delete_setup_variable(var_name){
    if(!Object.keys(instance_variables.value).includes(var_name)){
        return;
    }
    delete instance_variables.value[var_name];
}
function copy_setup_variable(varname){
    // instance_variables[varname] = structuredClone(workflow.value.setup_variables[varname]);
    instance_variables.value[varname] = JSON.parse(JSON.stringify(workflow.value.setup_variables[varname]));
}
</script>

<style>
.spawninstance_edit{
    width: 100%;
    height: 100%;
    position: fixed;
    top: 0;
    left: 0;
    background-color: rgba(128, 128, 128, 0.5);
}
.spawninstance_edit_content_section{
    margin: 3em;
    overflow: scroll;
    max-height: 90%;
}
</style>

<template>
    <div class="spawninstance_edit" @click.self="close_spawninstance_edit">
        <section class="spawninstance_edit_content_section">
            <button type="button" @click="close_spawninstance_edit">Cancel</button>
            <button type="button" @click="save_and_close_spawninstance_edit">Spawn</button>
            <div class="client_error_message" v-if="spawninstance_edit_state.client_error_message.length > 0">{{ spawninstance_edit_state.client_error_message }}</div>
            <h2>{{ workflow.name }}</h2>
            <p>Spawning a new instance</p>

            <div class="spawninstance_edit_variables">
                <Variable v-for="vname in missing_variables" :key="vname" :name="vname" :variable="workflow.setup_variables[vname]" @click="copy_setup_variable(vname)" />
            </div>
            <div class="spawninstance_edit_variables">
                <VariableEdit v-for="vname in expected_variables" :key="vname" v-model="instance_variables[vname]" @requested_deletion="delete_setup_variable(vname)">{{ vname }}</VariableEdit>
            </div>
            <div class="spawninstance_edit_variables" v-if="extra_variables.length > 0">
                Extra Variables:
                <VariableEdit v-for="vname in extra_variables" :key="vname" v-model="instance_variables[vname]" @requested_deletion="delete_setup_variable(vname)">{{ vname }}</VariableEdit>
            </div>
            <label>Add Variable</label>
            <input type="text" placeholder="Variable Name" v-model="new_setup_var_name"/>
            <button type="button" @click="add_new_setup_variable">Add</button>
        </section>
    </div>
</template>