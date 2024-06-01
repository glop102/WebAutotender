<script setup>
import Command from "./Command.vue";
const props = defineProps({
    name: String,
    commands: Array
});
</script>

<template>
    <div class="procedure_details">
        <div class="procedure_details_name">{{ name }}</div>
        <div class="procedure_details_commands">
            <Command v-for="c in commands" :command="c" />
        </div>
    </div>
</template>