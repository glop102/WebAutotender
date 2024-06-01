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
    display: inline-block;
}

.variable_details_typename {
    color: grey;
}
</style>

<template>
    <div class="variable_details">
        <div class="variable_details_name">{{ name }}</div>
        <div class="variable_details_typename">{{ variable.typename }}</div>
        <div class="variable_details_value">{{ variable.value }}</div>
    </div>
</template>