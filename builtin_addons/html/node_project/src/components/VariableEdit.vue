<script setup>
import {ref} from "vue"
import { variable_types } from "@/server_com";
const variable = defineModel();
const emits = defineEmits(['requested_deletion']);

function stringlist_push(){
    if(variable.value.value.constructor === String){
        if(variable.value.value.length == 0){
            variable.value.value = [];
        }else{
            variable.value.value = [variable.value.value];
        }
    }else if (variable.value.value.constructor !== Array){
        variable.value.value = [];
    }
    variable.value.value.push('');
}

const dictionary_field_new_name = ref("");
function dictionary_push(){
    if (variable.value.value.constructor !== Object){
        variable.value.value = {};
    }
    if (dictionary_field_new_name.value.length == 0){
        return;
    }
    if (Object.keys(variable.value.value).includes(dictionary_field_new_name.value)){
        return;
    }
    variable.value.value[dictionary_field_new_name.value]={"value":"","typename":"String"};
    dictionary_field_new_name.value="";
}
</script>

<style>
.variable_edit {
    display: inline-block;
    border: solid 0.1em;
    padding: 0.5em;
    margin: 0.25em;
    border-radius: 0.25em;
}

.variable_edit_name,
.variable_edit_typename {
    display: inline-block;
}
.variable_edit_value {
    display: block;
}
</style>

<template>
    <div class="variable_edit">
        <slot class="variable_edit_name"></slot>
        <select v-model="variable.typename">
            <option v-for="typename in variable_types" :value="typename">{{ typename }}</option>
        </select>
        <button type="button" @click="emits('requested_deletion')">Delete</button>
        <input v-if="'Integer'==variable.typename || 'Float'==variable.typename" type="number" class="variable_edit_value" v-model="variable.value"/>
        <div v-else-if="'StringList'==variable.typename || 'VariableNameList'==variable.typename">
            <div v-for="idx in variable.value.length" :key="idx-1">
                <button type="button" @click="variable.value.splice(idx-1,1)">X</button>
                <input type="text" v-model="variable.value[idx-1]"/>
            </div>
            <button type="button" @click="stringlist_push">+</button>
        </div>
        <div v-else-if="'Dictionary'==variable.typename">
            <VariableEdit v-for="vname in Object.keys(variable.value)" :key="vname" type="text" v-model="variable.value[vname]" @requested_deletion="delete variable.value[vname]">{{ vname }}</VariableEdit>
            <button type="button" @click="dictionary_push">+</button>
            <input type="text" v-model="dictionary_field_new_name" placeholder="Entry Name"/>
        </div>
        <input v-else type="text" class="variable_edit_value" v-model="variable.value"/> <!-- Default assume it is just a basic string -->
    </div>
</template>