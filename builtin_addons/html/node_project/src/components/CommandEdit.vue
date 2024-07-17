<script setup>
import {ref,computed} from 'vue'
import VariableEdit from './VariableEdit.vue'
import {available_commands,available_commands_names} from "@/server_com"

const data = defineModel();
const missing_variables = computed(
    () => Object.keys(available_commands.value[data.value.command_name].arguments).filter(
        (varname) => !Object.keys(data.value.variables).includes(varname)
    )
);
const expected_variables = computed(
    () => Object.keys(available_commands.value[data.value.command_name].arguments).filter(
        (varname) => Object.keys(data.value.variables).includes(varname)
    )
);
const extra_variables = computed(
    () => Object.keys(data.value.variables).filter(
        (varname) => !Object.keys(available_commands.value[data.value.command_name].arguments).includes(varname)
    )
);

function delete_command_variable(varname){
    if(!Object.keys(data.value.variables).includes(varname)){
        return;
    }
    delete data.value.variables[varname];
}
function add_command_variable(varname,typename){
    if(Object.keys(data.value.variables).includes(varname)){
        return;
    }
    data.value.variables[varname] = {
        "value": "",
        "typename": typename
    };
}
</script>

<style>
.command_edit_container{
    display: inline-block;
    border: solid 0.1em;
    padding: 0.5em;
}
.command_name_select{
    display: block;
}
</style>

<template>
    <div class="command_edit_container">
        <select class="command_name_select" v-model="data.command_name">
            <option v-for="cname in available_commands_names" :value="cname" :key="cname">{{ cname }}</option>
        </select>
        <div class="missing_variable" v-for="varname in missing_variables" :key="varname">{{ varname }}
            <button type="button"
                v-if="typeof available_commands[data.command_name].arguments[varname] == 'string'"
                @click="add_command_variable(varname,available_commands[data.command_name].arguments[varname])"
                >
                    {{ available_commands[data.command_name].arguments[varname] }}
            </button>
            <button type="button"
                v-if="typeof available_commands[data.command_name].arguments[varname] == 'object'"
                v-for="argtype in available_commands[data.command_name].arguments[varname]" :key="argtype"
                @click="add_command_variable(varname,argtype)"
                >
                    {{ argtype }}
            </button>
        </div>
        <div>
            <VariableEdit v-for="vname in expected_variables" :key="vname" v-model="data.variables[vname]" @requested_deletion="delete_command_variable(vname)">{{ vname }} - {{ available_commands[data.command_name].arguments[vname] }}</VariableEdit>
        </div>
        <div v-if="extra_variables.length>0">
            Extra Arguments:
            <VariableEdit v-for="vname in extra_variables" :key="vname" v-model="data.variables[vname]" @requested_deletion="delete_command_variable(vname)">{{ vname }}</VariableEdit>
        </div>
    </div>
</template>