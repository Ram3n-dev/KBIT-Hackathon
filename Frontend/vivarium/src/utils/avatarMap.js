// src/utils/avatarMap.js
import yellowSlime from "../img/icons/yellow_slime.svg";
import blueSlime from "../img/icons/blue_slime.svg";
import purpleSlime from "../img/icons/purple_slime.svg";
import redSlime from "../img/icons/red_slime.svg";
import lightBlueSlime from "../img/icons/light_blue_slime.svg";

export const avatarMap = {
  // По имени файла
  "yellow_slime.svg": yellowSlime,
  "blue_slime.svg": blueSlime,
  "purple_slime.svg": purpleSlime,
  "red_slime.svg": redSlime,
  "light_blue_slime.svg": lightBlueSlime,
};

export const avatarOptions = [
  { id: 1, file: "yellow_slime.svg", image: yellowSlime, color: "#5d6939", name: "Желтый слайм" },
  { id: 2, file: "blue_slime.svg", image: blueSlime, color: "#5d6939", name: "Синий слайм" },
  { id: 3, file: "purple_slime.svg", image: purpleSlime, color: "#5d6939", name: "Фиолетовый слайм" },
  { id: 4, file: "red_slime.svg", image: redSlime, color: "#5d6939", name: "Красный слайм" },
  { id: 5, file: "light_blue_slime.svg", image: lightBlueSlime, color: "#5d6939", name: "Голубой слайм" },
];

// Функция для получения аватарки по имени файла
export const getAvatarByFile = (fileName) => {
  return avatarMap[fileName] || yellowSlime;
};