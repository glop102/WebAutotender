<script setup>
import {ref} from "vue"
const props = defineProps({
    name: String,
    variable: Object
});
</script>

<style>
.variable_details {
    display: inline-block;
    border: solid 0.1em;
    padding: 0.5em;
    margin: 0.25em;
    border-radius: 0.25em;
}

.variable_details_name,
.variable_details_typename,
.variable_details_value {
    display: block;
}

.variable_details_typename {
    color: grey;
}
</style>

<template>
    <div class="variable_details">
        <div class="variable_details_name">{{ name }}</div>
        <div v-if="variable.typename=='StringList' || variable.typename=='VariableNameList'">
            <div class="variable_details_value" v-for="(v,idx) in variable.value" :key="idx">{{ v }}</div>
        </div>
        <div v-else-if="variable.typename=='Dictionary'">
            <Variable v-for="vname in Object.keys(variable.value)" :key="vname" :name="vname" :variable="variable.value[vname]"/>
        </div>
        <div v-else-if="variable.typename=='VariableList'">
            <Variable v-for="idx in variable.value.length" :key="idx-1" :variable="variable.value[idx-1]"/>
        </div>
        <div v-else class="variable_details_value">{{ variable.value }}</div>
    </div>
</template>