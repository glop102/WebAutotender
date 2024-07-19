<script setup>
import {global_variables,delete_global_variable,push_global_variable_state} from '@/server_com';
import {ref} from 'vue';
import Variable from './Variable.vue';
import VariableEdit from './VariableEdit.vue';

const props = defineProps({varname:String});
const editing = ref(false);

const global_var_tempspace = ref({});
function start_editing(){
    global_var_tempspace.value = JSON.parse(JSON.stringify(global_variables.value[props.varname]));
    editing.value = true;
}
function stop_editing(){
    editing.value = false;
}
function save_editing(){
    global_variables.value[props.varname] = JSON.parse(JSON.stringify(global_var_tempspace.value));
    push_global_variable_state(props.varname);
    stop_editing();
}
</script>

<style>
.global_variable_item{
    display: inline-block;
}
</style>

<template>
    <div class="global_variable_item">
        <button type="button" v-if="!editing" @click="start_editing">edit</button>
        <button type="button" v-if="editing" @click="stop_editing">cancel</button>
        <button type="button" v-if="editing" @click="save_editing">save</button>
        <br/>
        <Variable :name="props.varname" :variable="global_variables[props.varname]" v-if="!editing" />
        <VariableEdit v-model="global_var_tempspace" @requested_deletion="delete_global_variable(props.varname)" v-if="editing">{{ props.varname }}</VariableEdit>
    </div>
</template>